# agent-hub-core

Shared hardened core for JARVIS agents. Every agent in this repository depends on
this one implementation instead of copy-pasting safety-critical modules.

## What it provides

- **Sandboxed executor** (`agent_hub_core.executor`): runs LLM-generated analysis
  code under an AST allow-list (imports, builtins, dunder access) plus a deny-list
  of I/O-capable pandas/numpy method calls, in a separate process with a hard
  wall-clock timeout. No file or network I/O is possible from generated code.
- **Model-agnostic LLM client** (`agent_hub_core.llm`): a single
  `get_client()` returning a `.complete(system, prompt)` client for Claude
  (Anthropic), local Ollama models, or a deterministic offline stub. Configuration
  is read from the environment at instantiation time, never at import time.
- **Structured tracing** (`agent_hub_core.tracing`): JSON-to-stdout logging with a
  contextvars-based trace id, so multi-agent JARVIS requests correlate across
  agents and log aggregators.

## Installation

Editable install during development, from the repository root:

```bash
pip install -e ./agent-hub-core
```

## Placement

This package is a dependency consumed by other agents in `agents-of-jarvis/`
(for example `insight-agent/`). It is not a standalone service: it has no API
surface, no entry point, and nothing to deploy on its own.
