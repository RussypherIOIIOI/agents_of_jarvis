"""FastAPI backend for Insight Agent.

Endpoints:
  GET  /            -> serves the web UI
  GET  /health      -> liveness probe
  POST /upload      -> upload a CSV, returns a dataset id + schema
  POST /ask         -> ask a question about an uploaded dataset

Datasets are held in memory keyed by id (fine for a single-user demo). For
multi-user production, back this with a store and per-session isolation.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from agent_hub_core.tracing import TRACE_HEADER, get_logger, new_trace_id, trace_id_var
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import analyze
from .data import Dataset, load_csv_bytes

logger = get_logger("insight_agent.api")

app = FastAPI(title="Insight Agent", version="1.0.0")


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Thread an upstream trace id (or a fresh one) through the request."""
    trace_id = request.headers.get(TRACE_HEADER) or new_trace_id()
    token = trace_id_var.set(trace_id)
    try:
        response = await call_next(request)
    finally:
        trace_id_var.reset(token)
    response.headers[TRACE_HEADER] = trace_id
    return response

_DATASETS: dict[str, Dataset] = {}
_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


class AskRequest(BaseModel):
    dataset_id: str
    question: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="please upload a .csv file")
    raw = await file.read()
    try:
        dataset = load_csv_bytes(raw, name=Path(file.filename).stem)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"could not parse CSV: {exc}") from exc

    dataset_id = uuid.uuid4().hex[:12]
    _DATASETS[dataset_id] = dataset
    return {
        "dataset_id": dataset_id,
        "name": dataset.name,
        "rows": len(dataset.df),
        "columns": list(dataset.df.columns),
        "schema": dataset.schema_summary(),
    }


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    dataset = _DATASETS.get(req.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="unknown dataset_id; upload first")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")

    try:
        result = analyze(req.question, dataset)
    except Exception:
        # Log the full exception server-side; surface a structured error to the
        # caller without leaking stack traces, keys, or internal paths.
        logger.exception("analysis failed for dataset_id=%s", req.dataset_id)
        raise HTTPException(
            status_code=502,
            detail="analysis failed: the upstream LLM provider returned an error "
            "or was unreachable; please retry",
        ) from None
    return {
        "answer": result.answer,
        "code": result.code,
        "chart_png_base64": result.chart_png_base64,
        "raw_output": result.raw_output,
        "error": result.error,
        "steps": result.steps,
        "trace_id": trace_id_var.get(),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_FRONTEND / "index.html"))


# Serve static assets if present (css/js).
if _FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")
