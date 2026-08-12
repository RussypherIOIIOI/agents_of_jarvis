"""Dataset loading for CSV and SQLite sources, plus a schema summary the agent
uses to reason about the data.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class Dataset:
    df: pd.DataFrame
    name: str

    def schema_summary(self, max_rows: int = 3) -> str:
        """Compact, LLM-friendly description of the data: columns, dtypes, sample."""
        lines = [f"Dataset '{self.name}' with {len(self.df)} rows and "
                 f"{len(self.df.columns)} columns.", "", "Columns:"]
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            nun = self.df[col].nunique(dropna=True)
            lines.append(f"  - {col} ({dtype}, {nun} unique)")
        lines.append("")
        lines.append("Sample rows:")
        lines.append(self.df.head(max_rows).to_string(index=False))
        return "\n".join(lines)


def load_csv(path: str | Path, name: str | None = None) -> Dataset:
    df = pd.read_csv(path)
    return Dataset(df=df, name=name or Path(path).stem)


def load_sqlite(db_path: str | Path, table: str) -> Dataset:
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    return Dataset(df=df, name=table)


def load_csv_bytes(raw: bytes, name: str) -> Dataset:
    import io

    df = pd.read_csv(io.BytesIO(raw))
    return Dataset(df=df, name=name)
