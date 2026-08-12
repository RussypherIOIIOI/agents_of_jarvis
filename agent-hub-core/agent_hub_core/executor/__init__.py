"""Sandboxed execution of LLM-generated analysis code.

Generated code is never trusted. Before running, it is parsed and checked against
an allow-list: no disallowed imports, no dunder/attribute escapes, no dangerous
builtins. Execution happens in a restricted namespace with a wall-clock timeout,
exposing only the DataFrame and a safe subset of pandas / matplotlib.

For a portfolio/demo this is a strong, transparent default. For untrusted
multi-tenant production, additionally isolate each run in a container/microVM.
"""
from __future__ import annotations

import ast
import base64
import io
import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Any

# Imports the generated code is allowed to reference.
ALLOWED_IMPORTS = {"pandas", "pd", "numpy", "np", "matplotlib", "plt", "math", "statistics"}

# Builtins that are explicitly forbidden even if referenced.
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
}

# I/O-capable pandas/numpy methods that could read or write files, databases,
# or network resources. Blocked outright regardless of the receiver object:
# the DataFrame is injected into the namespace, so generated code has no
# legitimate reason to perform any file or network I/O.
FORBIDDEN_IO_CALLS = {
    "read_csv", "read_excel", "read_json", "read_sql", "read_sql_query",
    "read_sql_table", "read_parquet", "read_pickle", "read_html",
    "read_feather", "read_orc", "read_hdf", "read_gbq",
    "to_csv", "to_excel", "to_json", "to_sql", "to_parquet", "to_pickle",
    "to_hdf", "to_feather", "to_html",
}


@dataclass
class ExecResult:
    ok: bool
    stdout: str = ""
    result_repr: str = ""
    chart_png_base64: str | None = None
    error: str | None = None
    columns: list[str] = field(default_factory=list)


class CodeSafetyError(Exception):
    """Raised when generated code violates the safety allow-list."""


def validate_code(code: str) -> None:
    """Static analysis gate. Raises CodeSafetyError on any violation."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeSafetyError(f"syntax error: {exc}") from exc

    for node in ast.walk(tree):
        # Block dunder attribute access (a common sandbox escape).
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise CodeSafetyError(f"disallowed dunder attribute: {node.attr}")

        # Restrict imports to the allow-list.
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    raise CodeSafetyError(f"disallowed import: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                raise CodeSafetyError(f"disallowed import from: {node.module}")

        # Block forbidden names used as calls or references.
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise CodeSafetyError(f"disallowed name: {node.id}")

        # Block file/network I/O via pandas/numpy method calls, regardless of
        # the object they are called on (df.to_csv, pd.read_csv, chained calls).
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in FORBIDDEN_IO_CALLS
        ):
            raise CodeSafetyError(f"disallowed I/O call: {node.func.attr}")


def _worker(code: str, df_records: list[dict], columns: list[str], q: mp.Queue) -> None:
    """Runs in a separate process so a timeout can hard-kill it."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

        df = pd.DataFrame.from_records(df_records)

        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Statement was already validated by validate_code(); this simply
            # allows the interpreter to bind names already injected below.
            if name.split(".")[0] not in ALLOWED_IMPORTS:
                raise ImportError(f"import of '{name}' is not permitted")
            return __import__(name, globals, locals, fromlist, level)

        safe_builtins = {
            "len": len, "range": range, "min": min, "max": max, "sum": sum,
            "sorted": sorted, "round": round, "abs": abs, "list": list,
            "dict": dict, "set": set, "tuple": tuple, "enumerate": enumerate,
            "zip": zip, "float": float, "int": int, "str": str, "bool": bool,
            "print": print, "__import__": _safe_import,
        }
        namespace: dict[str, Any] = {
            "__builtins__": safe_builtins,
            "df": df, "pd": pd, "np": np, "plt": plt,
        }

        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            exec(code, namespace)  # noqa: S102 - guarded by validate_code + sandbox

        result = namespace.get("result")
        result_repr = "" if result is None else str(result)[:5000]

        chart_b64 = None
        if plt.get_fignums():
            img = io.BytesIO()
            plt.savefig(img, format="png", bbox_inches="tight", dpi=100)
            plt.close("all")
            chart_b64 = base64.b64encode(img.getvalue()).decode("ascii")

        q.put(ExecResult(
            ok=True,
            stdout=buf.getvalue()[:5000],
            result_repr=result_repr,
            chart_png_base64=chart_b64,
            columns=list(df.columns),
        ))
    except Exception as exc:  # never propagate; report structurally
        q.put(ExecResult(ok=False, error=f"{type(exc).__name__}: {exc}"))


def run_code(code: str, df, timeout: float = 15.0) -> ExecResult:
    """Validate then execute generated code against `df` with a timeout."""
    try:
        validate_code(code)
    except CodeSafetyError as exc:
        return ExecResult(ok=False, error=f"blocked by safety check: {exc}")

    records = df.to_dict(orient="records")
    columns = list(df.columns)

    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_worker, args=(code, records, columns, q))
    proc.start()
    proc.join(timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return ExecResult(ok=False, error=f"execution timed out after {timeout}s")

    try:
        return q.get_nowait()
    except Exception:
        return ExecResult(ok=False, error="no result returned from executor")
