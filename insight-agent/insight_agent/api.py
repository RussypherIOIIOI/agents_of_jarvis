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

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import analyze
from .data import Dataset, load_csv_bytes

app = FastAPI(title="Insight Agent", version="1.0.0")

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

    result = analyze(req.question, dataset)
    return {
        "answer": result.answer,
        "code": result.code,
        "chart_png_base64": result.chart_png_base64,
        "raw_output": result.raw_output,
        "error": result.error,
        "steps": result.steps,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_FRONTEND / "index.html"))


# Serve static assets if present (css/js).
if _FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")
