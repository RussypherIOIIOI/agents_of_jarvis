# Portfolio and Resume Assets

Copy-paste text for your resume, LinkedIn, and portfolio site. Replace the
bracketed links after you push to GitHub and deploy.

## Resume bullets (pick one or two)

- Built Insight Agent, an open-source conversational data-analyst that turns
  plain-English questions into executed pandas/SQL analysis, charts, and grounded
  explanations, using an LLM agent loop (plan, generate code, sandboxed execute,
  reflect, explain) over a FastAPI backend.
- Engineered a secure code-execution sandbox (AST allow-listing, restricted
  namespace, process isolation, and timeouts) that safely runs LLM-generated
  analysis code, backed by a pytest suite and GitHub Actions CI.
- Delivered the project end to end: Python package, web UI, Docker/compose
  packaging, CI/CD, and documentation, with pluggable model providers (Claude API
  or local Ollama).

## LinkedIn / portfolio blurb

Insight Agent is an open-source conversational data analyst. Upload a CSV, ask a
question in plain English, and it writes the analysis code, runs it in a secure
sandbox, generates a chart, and explains the finding, grounded in your data. Built
with Python, FastAPI, pandas, and an LLM agent loop, with a full test suite,
GitHub Actions CI, and Docker packaging. Works with Claude or a free local model.

Repository: [your repo link]
Live demo: [your demo link]

## One-line summary

An AI data analyst you can talk to: plain-English questions in, charts and grounded
insights out, with safely sandboxed code execution.

## Talking points for interviews

- Why the executor is designed the way it is, and the threat model it addresses.
- The reflect-and-retry step and how it improves reliability of generated code.
- The tradeoffs of in-memory storage for a demo versus a production session store.
- How the model layer keeps the system provider-agnostic and testable offline.
