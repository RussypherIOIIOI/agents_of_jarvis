"""Optional LangGraph implementation of the same pipeline.

The default `analyze()` in this package is dependency-light and used by the API
and tests. This module offers an equivalent graph for those who prefer the
LangGraph abstraction (plan -> code -> execute -> reflect -> explain).

Import lazily so the core project runs without langgraph installed.
"""
from __future__ import annotations

from typing import Any, TypedDict

from ..data import Dataset
from ..executor import run_code
from ..llm import get_client
from . import CODE_SYSTEM, EXPLAIN_SYSTEM, _extract_code


class GraphState(TypedDict, total=False):
    question: str
    schema: str
    code: str
    output: str
    chart: str | None
    error: str | None
    answer: str
    attempts: int


def build_graph(dataset: Dataset):
    """Compile and return a LangGraph app that analyzes `dataset`."""
    from langgraph.graph import END, START, StateGraph

    llm = get_client()

    def code_node(state: GraphState) -> dict[str, Any]:
        prompt = f"SCHEMA:\n{state['schema']}\n\nQUESTION: {state['question']}"
        if state.get("error"):
            prompt += f"\n\nPrevious code failed with:\n{state['error']}\nFix it."
        code = _extract_code(llm.complete(CODE_SYSTEM, prompt))
        return {"code": code, "attempts": state.get("attempts", 0) + 1}

    def exec_node(state: GraphState) -> dict[str, Any]:
        r = run_code(state["code"], dataset.df)
        if r.ok:
            return {"output": (r.stdout + "\n" + r.result_repr).strip(),
                    "chart": r.chart_png_base64, "error": None}
        return {"error": r.error}

    def route(state: GraphState) -> str:
        if state.get("error") and state.get("attempts", 0) <= 2:
            return "code"
        return "explain"

    def explain_node(state: GraphState) -> dict[str, Any]:
        if state.get("error"):
            return {"answer": f"Analysis failed: {state['error']}"}
        answer = llm.complete(
            EXPLAIN_SYSTEM,
            f"QUESTION: {state['question']}\n\nCODE:\n{state['code']}\n\n"
            f"OUTPUT:\n{state['output']}",
        )
        return {"answer": answer.strip()}

    g = StateGraph(GraphState)
    g.add_node("code", code_node)
    g.add_node("execute", exec_node)
    g.add_node("explain", explain_node)
    g.add_edge(START, "code")
    g.add_edge("code", "execute")
    g.add_conditional_edges("execute", route, {"code": "code", "explain": "explain"})
    g.add_edge("explain", END)
    return g.compile()
