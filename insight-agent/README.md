<div align="center">

# Insight Agent

**A conversational data analyst you can talk to. Upload a CSV or connect a database, ask questions in plain English, and get charts, statistics, and clear explanations grounded in your data.**

[![CI](https://github.com/your-handle/insight-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/your-handle/insight-agent/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)

</div>

---

## What it does

Insight Agent turns a dataset and a plain-English question into a real analysis. Ask *"What drove the revenue drop in Q3?"* or *"Show me the correlation between marketing spend and signups"* and the agent will:

1. **Plan** the analysis steps.
2. **Write** Python (pandas) or SQL to answer the question.
3. **Execute** that code in a sandboxed environment.
4. **Visualize** the result as a chart when appropriate.
5. **Explain** the finding in clear language, grounded in the actual data.

No manual scripting. No copy-pasting into a notebook. Just a conversation with your data.

---

## Demo

> Replace the placeholders below with a screen recording / screenshot once you run it locally or view the live demo.

![Insight Agent demo](docs/demo.gif)

**Live demo (UI):** deploy your own instance and add the link here (see Quickstart).

---

## Why this project

This repository demonstrates end-to-end ownership of an AI-powered data product: from the analytical reasoning loop, to safe code execution, to a production-style API, to CI/CD and containerized deployment. It sits at the intersection of **data analysis** and **full-stack engineering**.

### Skills demonstrated

| Area | What is shown here |
|------|--------------------|
| AI agents | Stateful LangGraph loop: plan -> generate code -> execute -> reflect -> explain |
| Data analysis | pandas + SQL analysis, descriptive statistics, correlation, aggregation |
| Visualization | Automated matplotlib chart generation from natural-language requests |
| Backend | FastAPI service with file upload, chat, and chart endpoints |
| Frontend | Lightweight web UI for upload + chat + chart display |
| Safety | Sandboxed code execution with import/attribute allow-lists and timeouts |
| Testing | pytest suite covering the executor, tools, and API (TDD-friendly) |
| DevOps | GitHub Actions CI (lint + test) and Docker / docker-compose |
| Model flexibility | Works with Claude (API) or a local Ollama model (free, offline) |

---

## Architecture

```
        Browser UI (upload CSV, chat, charts)
                     |
                     v
            FastAPI backend  ──────────────┐
                     |                       │  traces
                     v                       v
        LangGraph agent loop           (optional) logs
   plan → code → execute → reflect → explain
     |          |            |
     v          v            v
  LLM       Sandboxed     Chart
 client     executor     generator
(Claude/    (pandas/     (matplotlib)
 Ollama)     sqlite)
```

The agent never runs raw model output blindly: generated code is validated against an allow-list and executed with a timeout inside a restricted namespace. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

---

## Quickstart

### Option A - Local (Python)

```bash
git clone https://github.com/your-handle/insight-agent.git
cd insight-agent

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env          # add ANTHROPIC_API_KEY, or use Ollama (below)

uvicorn insight_agent.api:app --reload
# open http://localhost:8000
```

### Option B - Local with Ollama (no API key, fully offline)

```bash
# Install Ollama from https://ollama.com, then:
ollama pull llama3.1
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1
uvicorn insight_agent.api:app --reload
```

### Option C - Docker (one command)

```bash
docker compose up --build
# open http://localhost:8000
```

Then upload the bundled sample dataset at [`sample_data/sales.csv`](sample_data/sales.csv) and try:

- "What were total sales by region?"
- "Plot monthly revenue over time."
- "Which product category has the highest average order value?"

---

## Example

**Question:** "What is the correlation between marketing spend and signups?"

**Insight Agent responds:**

> There is a strong positive correlation (r = 0.87) between marketing spend and signups. On average, each additional \$1,000 in spend is associated with roughly 42 more signups. The relationship is fairly linear except for the two highest-spend weeks, where returns diminish.
>
> *Chart: scatter of marketing_spend vs signups with a fitted trend line.*
>
> *Grounded in: 52 rows of `sales.csv`, columns `marketing_spend`, `signups`.*

---

## Project structure

```
insight-agent/
├── insight_agent/
│   ├── agent/            # LangGraph state machine (plan/code/execute/explain)
│   ├── data/             # CSV / SQLite loading
│   └── api.py            # FastAPI app

The sandboxed executor, LLM client layer, and structured tracing live in the
sibling `agent-hub-core` package: one hardened source of truth shared by all
JARVIS agents instead of per-agent copies.
├── frontend/             # Web UI (HTML/CSS/JS)
├── tests/                # pytest suite
├── sample_data/          # sales.csv for a quick try
├── docs/                 # architecture + demo assets
├── .github/workflows/    # CI (lint + test)
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Testing

```bash
pytest -v          # run the suite
ruff check .       # lint
```

CI runs both on every push and pull request (see the badge at the top).

---

## Security notes

Generated code is not trusted. The executor:

- parses the code and rejects disallowed imports, dunder access, and dangerous builtins,
- runs inside a restricted namespace exposing only the loaded DataFrame and a safe subset of pandas/matplotlib,
- enforces a wall-clock timeout,
- captures output instead of allowing arbitrary side effects.

This is a strong default for a portfolio/demo project. For untrusted multi-tenant use, run the executor in a container or microVM per request.

---

## Roadmap

- [ ] Multi-file / multi-table joins
- [ ] Postgres and Snowflake connectors
- [ ] Downloadable analysis report (PDF)
- [ ] Session memory across questions
- [ ] Streaming responses in the UI

---

## License

MIT - see [LICENSE](LICENSE). Contributions welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

---

<div align="center">
Built as a demonstration of end-to-end AI + data engineering.
</div>
