"""Tests for dataset loading and schema summaries."""
from __future__ import annotations

from insight_agent.data import load_csv_bytes


def test_load_csv_bytes_parses():
    raw = b"name,age\nalice,30\nbob,25\n"
    ds = load_csv_bytes(raw, name="people")
    assert ds.name == "people"
    assert len(ds.df) == 2
    assert list(ds.df.columns) == ["name", "age"]


def test_schema_summary_describes_columns():
    raw = b"region,sales\nnorth,100\nsouth,200\n"
    ds = load_csv_bytes(raw, name="sales")
    summary = ds.schema_summary()
    assert "region" in summary
    assert "sales" in summary
    assert "2 rows" in summary
