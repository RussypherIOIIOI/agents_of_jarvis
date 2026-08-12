"""The Insight Agent reasoning loop.

Pipeline: plan -> generate code -> execute (sandboxed) -> reflect/retry -> explain.

Implemented as a small, dependency-light state machine. It is intentionally
readable so reviewers can follow the control flow. A LangGraph variant is
available in `graph.py` for those who want the graph abstraction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..data import Dataset
from ..executor import ExecResult, run_code
from ..llm import BaseLLM, get_client

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
        steps.append(f"plan/code (attempt {attempt + 1})")
        prompt = f"SCHEMA:\n{schema}\n\nQUESTION: {question}"
        if last_error:
            prompt += (
                f"\n\nThe previous code failed with:\n{last_error}\n"
                "Fix it and return corrected Python."
            )
        code = _extract_code(llm.complete(CODE_SYSTEM, prompt))

        steps.append("execute (sandboxed)")
        exec_result = run_code(code, dataset.df)

        if exec_result.ok:
            break
        last_error = exec_result.error
        steps.append(f"error: {last_error}")

    if not exec_result or not exec_result.ok:
        return AgentResult(
            answer="I could not complete the analysis safely.",
            code=code,
            error=(exec_result.error if exec_result else "no execution result"),
            steps=steps,
        )

    steps.append("explain")
    output_blob = (exec_result.stdout + "\n" + exec_result.result_repr).strip()
    explanation = llm.complete(
        EXPLAIN_SYSTEM,
        f"QUESTION: {question}\n\nCODE:\n{code}\n\nOUTPUT:\n{output_blob}",
    )

    return AgentResult(
        answer=explanation.strip(),
        code=code,
        chart_png_base64=exec_result.chart_png_base64,
        raw_output=output_blob,
        steps=steps,
    )
