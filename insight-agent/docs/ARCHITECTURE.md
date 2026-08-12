# Architecture

Insight Agent is a small, readable AI data-analysis system. This document explains
how the pieces fit together and the design decisions behind them.

## Overview

```
Browser UI  ->  FastAPI  ->  Agent loop  ->  { LLM, Sandbox, Charts }
```

A user uploads a CSV and asks a question. The backend runs an agent loop that
writes analysis code with an LLM, executes it safely, and returns an explanation
plus an optional chart.

## The agent loop

`insight_agent/agent/__init__.py` implements the pipeline:

1. **Plan and generate code.** The LLM receives a compact schema summary (columns,
   dtypes, sample rows) and the question, and returns pandas/matplotlib code that
   assigns the answer to a `result` variable.
2. **Execute (sandboxed).** The code runs through the executor (below).
3. **Reflect and retry.** If execution fails, the error is fed back to the LLM for
   one corrective attempt.
4. **Explain.** The LLM turns the code output into a stakeholder-ready explanation,
   instructed not to invent numbers absent from the output.

A `graph.py` variant implements the same flow with LangGraph for those who prefer
the graph abstraction; the default path is dependency-light for clarity and testing.

## The executor (safety-critical)

`insight_agent/executor/__init__.py` never trusts model output.

- **Static validation (`validate_code`).** The code is parsed to an AST and rejected
  if it imports anything outside an allow-list, accesses dunder attributes, or uses
  forbidden names (`eval`, `exec`, `open`, `os`, `subprocess`, and so on).
- **Restricted execution.** Validated code runs in a namespace exposing only the
  DataFrame and a safe subset of pandas, numpy, and matplotlib, with a curated set
  of builtins.
- **Process isolation and timeout.** Execution happens in a separate spawned process
  that is hard-killed if it exceeds the wall-clock timeout, preventing runaway loops.
- **Captured output.** Stdout, the `result` value, and any matplotlib figure are
  captured and returned; nothing else can leak out.

This is a strong, transparent default suitable for a portfolio and single-user demo.
For untrusted multi-tenant production, run each execution inside its own container or
microVM and add resource limits (CPU, memory, no network).

## Model layer

`insight_agent/llm/__init__.py` abstracts the provider behind a single `complete`
method:

- **Anthropic (Claude)** for high-quality reasoning when an API key is present.
- **Ollama** for a free, offline, local model.
- **Echo stub** as a deterministic fallback so the app and tests run with no key and
  no network.

The provider is chosen by environment variables, so switching models requires no code
changes.

## Backend

`insight_agent/api.py` is a small FastAPI app: `/upload` parses a CSV into an
in-memory dataset, `/ask` runs the agent, and `/` serves the UI. In-memory storage is
intentional for a single-user demo; a production build would add a session store and
per-user isolation.

## Testing

The suite in `tests/` covers the executor's safety guarantees (blocking unsafe code,
timeouts, error handling), data loading, the end-to-end agent path (via the offline
stub), and the API. CI runs lint and tests on every push and pull request across
Python 3.11 and 3.12.
