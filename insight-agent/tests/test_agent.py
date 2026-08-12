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
