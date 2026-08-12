"""API smoke tests using FastAPI's TestClient (offline via EchoLLM fallback)."""
from __future__ import annotations

import io

from fastapi.testclient import TestClient

from insight_agent.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_and_ask_flow():
    csv = b"region,sales\nnorth,100\nsouth,200\n"
    files = {"file": ("sales.csv", io.BytesIO(csv), "text/csv")}
    up = client.post("/upload", files=files)
    assert up.status_code == 200
    dataset_id = up.json()["dataset_id"]
    assert up.json()["rows"] == 2

    ask = client.post("/ask", json={"dataset_id": dataset_id, "question": "Describe it."})
    assert ask.status_code == 200
    body = ask.json()
    assert "answer" in body


def test_upload_rejects_non_csv():
    files = {"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = client.post("/upload", files=files)
    assert resp.status_code == 400


def test_ask_unknown_dataset():
    resp = client.post("/ask", json={"dataset_id": "does-not-exist", "question": "hi"})
    assert resp.status_code == 404
