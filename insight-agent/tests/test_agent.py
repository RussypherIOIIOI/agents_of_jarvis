"""End-to-end agent test using the offline EchoLLM stub (no API key/network)."""
from __future__ import annotations

from agent_hub_core.llm import EchoLLM, LLMConfig

from insight_agent.agent import analyze
from insight_agent.data import load_csv_bytes


def test_analyze_runs_end_to_end_offline():
    raw = b"region,sales\nnorth,100\nsouth,200\neast,150\n"
    ds = load_csv_bytes(raw, name="sales")
    llm = EchoLLM(LLMConfig(provider="echo"))

    result = analyze("Describe the data.", ds, llm=llm)

    # The stub returns `result = df.describe()`, which executes successfully.
    assert result.error is None
    assert result.code != ""
    assert "execute (sandboxed)" in result.steps
    assert isinstance(result.answer, str) and result.answer

    # Steps must record the pipeline stages in order (backward-compatible
    # contract for callers and the UI after the structured-logging change).
    plan_idx = result.steps.index("plan/code (attempt 1)")
    execute_idx = result.steps.index("execute (sandboxed)")
    explain_idx = result.steps.index("explain")
    assert plan_idx < execute_idx < explain_idx


class FailingCodeLLM:
    """Stub that always emits code that raises at execution time."""

    def complete(self, system: str, prompt: str) -> str:
        return "```python\nresult = 1 / 0\n```"


def test_analyze_records_error_steps_on_execution_failure():
    raw = b"region,sales\nnorth,100\nsouth,200\n"
    ds = load_csv_bytes(raw, name="sales")

    result = analyze("Break please.", ds, llm=FailingCodeLLM(), max_retries=1)

    assert result.error is not None
    error_steps = [s for s in result.steps if s.startswith("error:")]
    # One error step per failed attempt (initial try plus one retry).
    assert len(error_steps) == 2
    execute_idx = result.steps.index("execute (sandboxed)")
    first_error_idx = result.steps.index(error_steps[0])
    assert execute_idx < first_error_idx
    assert "explain" not in result.steps
