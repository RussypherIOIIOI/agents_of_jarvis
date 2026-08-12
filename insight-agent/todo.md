# insight-agent - Build Plan

## Repo Foundation
- [x] README.md (recruiter-friendly, badges, skills, architecture)
- [x] LICENSE (MIT)
- [x] CONTRIBUTING.md
- [x] .gitignore
- [x] pyproject.toml
- [x] .env.example

## Core Agent
- [x] agent state + loop (plan -> code -> execute -> reflect -> explain)
- [x] LangGraph variant (graph.py)
- [x] LLM client layer (Claude + Ollama + offline stub)
- [x] safe sandboxed code executor (AST allow-list, process isolation, timeout)
- [x] data loader (CSV / SQLite)
- [x] chart generation (matplotlib, base64)

## Backend
- [x] FastAPI app (upload, ask, health, serves UI)

## Frontend
- [x] Web UI (upload CSV, chat, view charts, view code)

## Quality
- [x] pytest test suite (17 tests, all passing)
- [x] GitHub Actions CI (lint + test, py3.11/3.12)
- [x] ruff config, lint clean

## Deploy
- [x] Dockerfile + docker-compose
- [x] Live demo deployed and verified

## Portfolio Extras
- [x] Sample dataset (sales.csv)
- [x] docs/ARCHITECTURE.md
- [x] docs/PORTFOLIO.md (resume bullets + LinkedIn blurb)
- [x] Verified end-to-end (upload + ask working)
- [x] Final packaging
