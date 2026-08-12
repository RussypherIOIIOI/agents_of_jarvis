"""The Insight Agent reasoning loop.

Pipeline: plan -> generate code -> execute (sandboxed) -> reflect/retry -> explain.

Implemented as a small, dependency-light state machine. It is intentionally
readable so reviewers can follow the control flow. A LangGraph variant is
available in `graph.py` for those who want the graph abstraction.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from agent_hub_core.executor import ExecResult, run_code
from agent_hub_core.llm import BaseLLM, get_client
from agent_hub_core.tracing import get_logger

from ..data import Dataset

logger = get_logger("insight_agent.agent")

CODE_SYSTEM = (
    "You are a senior data analyst. Given a dataset schema and a question, write "
    "Python using pandas (available as `pd`, `np`, `plt`) to answer it. The "
    "DataFrame is available as `df`. Assign the final answer to a variable named "
    "`result`. If a chart helps, create it with matplotlib (do not call plt.show). "
    "Return ONLY Python inside a single ```python code block. No prose."
)

EXPLAIN_SYSTEM = (
    "You are a senior data analyst. Given a question, the code that was run, and "
    "its output, write a concise, insight-driven explanation for a business "
    "stakeholder. State the finding first, then the supporting evidence. Do not "
    "invent numbers that are not in the output."
)


@dataclass
class AgentResult:
    answer: str
    code: str = ""
    chart_png_base64: str | None = None
    raw_output: str = ""
    error: str | None = None
    steps: list[str] = field(default_factory=list)


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def _log_stage(steps: list[str], step_label: str, stage: str, attempt: int,
               elapsed_ms: float, **fields) -> None:
    """Emit one structured log event per pipeline stage.

    `steps` on AgentResult is populated from the same events for backward
    compatibility with the existing tests and UI; the structured log line
    (which also carries the trace id via the formatter) is the primary record.
    """
    steps.append(step_label)
    logger.info(
        step_label,
        extra={"stage": stage, "attempt": attempt,
               "elapsed_ms": round(elapsed_ms, 2), **fields},
    )


def analyze(
    question: str,
    dataset: Dataset,
    llm: BaseLLM | None = None,
    max_retries: int = 1,
) -> AgentResult:
    """Answer `question` about `dataset` end to end."""
    llm = llm or get_client()
    steps: list[str] = []
    schema = dataset.schema_summary()

    last_error: str | None = None
    exec_result: ExecResult | None = None
    code = ""

    for attempt in range(max_retries + 1):
        stage_start = time.perf_counter()
        prompt = f"SCHEMA:\n{schema}\n\nQUESTION: {question}"
        if last_error:
            prompt += (
                f"\n\nThe previous code failed with:\n{last_error}\n"
                "Fix it and return corrected Python."
            )
        code = _extract_code(llm.complete(CODE_SYSTEM, prompt))
        _log_stage(steps, f"plan/code (attempt {attempt + 1})", "plan/code",
                   attempt + 1, (time.perf_counter() - stage_start) * 1000)

        stage_start = time.perf_counter()
        exec_result = run_code(code, dataset.df)
        _log_stage(steps, "execute (sandboxed)", "execute",
                   attempt + 1, (time.perf_counter() - stage_start) * 1000,
                   ok=exec_result.ok)

        if exec_result.ok:
            break
        last_error = exec_result.error
        stage_start = time.perf_counter()
        _log_stage(steps, f"error: {last_error}", "error",
                   attempt + 1, (time.perf_counter() - stage_start) * 1000,
                   error=last_error)

    if not exec_result or not exec_result.ok:
        return AgentResult(
            answer="I could not complete the analysis safely.",
            code=code,
            error=(exec_result.error if exec_result else "no execution result"),
            steps=steps,
        )

    stage_start = time.perf_counter()
    output_blob = (exec_result.stdout + "\n" + exec_result.result_repr).strip()
    explanation = llm.complete(
        EXPLAIN_SYSTEM,
        f"QUESTION: {question}\n\nCODE:\n{code}\n\nOUTPUT:\n{output_blob}",
    )
    _log_stage(steps, "explain", "explain", attempt + 1,
               (time.perf_counter() - stage_start) * 1000)

    return AgentResult(
        answer=explanation.strip(),
        code=code,
        chart_png_base64=exec_result.chart_png_base64,
        raw_output=output_blob,
        steps=steps,
    )
