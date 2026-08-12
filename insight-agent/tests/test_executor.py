"""Tests for the sandboxed executor: the most safety-critical component."""
from __future__ import annotations

import pandas as pd
import pytest

from insight_agent.executor import CodeSafetyError, run_code, validate_code


@pytest.fixture
def df():
    return pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})


def test_validate_code_allows_safe_pandas():
    validate_code("result = df['a'].sum()")


def test_validate_code_blocks_os_import():
    with pytest.raises(CodeSafetyError):
        validate_code("import os\nresult = os.listdir('.')")


def test_validate_code_blocks_dunder_access():
    with pytest.raises(CodeSafetyError):
        validate_code("result = df.__class__.__bases__")


def test_validate_code_blocks_eval():
    with pytest.raises(CodeSafetyError):
        validate_code("result = eval('1+1')")


def test_validate_code_blocks_open():
    with pytest.raises(CodeSafetyError):
        validate_code("f = open('/etc/passwd')\nresult = f.read()")


def test_run_code_executes_valid_analysis(df):
    result = run_code("result = df['a'].sum()", df)
    assert result.ok is True
    assert "6" in result.result_repr


def test_run_code_reports_error_without_crashing(df):
    result = run_code("result = 1 / 0", df)
    assert result.ok is False
    assert "ZeroDivisionError" in result.error


def test_run_code_blocks_unsafe_code_before_execution(df):
    result = run_code("import socket\nresult = socket.socket()", df)
    assert result.ok is False
    assert "blocked by safety check" in result.error


def test_run_code_times_out_on_infinite_loop(df):
    result = run_code("while True:\n    pass", df)
    assert result.ok is False
    assert "timed out" in result.error


def test_run_code_captures_chart(df):
    code = (
        "import matplotlib.pyplot as plt\n"
        "plt.plot(df['a'], df['b'])\n"
        "result = 'chart created'\n"
    )
    result = run_code(code, df)
    assert result.ok is True
    assert result.chart_png_base64 is not None
