# Contributing to Insight Agent

Contributions are welcome. This guide keeps changes consistent and easy to review.

## Getting started

```bash
git clone https://github.com/your-handle/insight-agent.git
cd insight-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a pull request

Run the checks locally; CI runs the same ones.

```bash
ruff check .        # lint
pytest -v           # tests
```

## Guidelines

- Keep the sandboxed executor conservative. Any change that widens what generated
  code can do must include tests demonstrating it is still safe.
- Add or update tests for any behavior change. This project favors test-driven
  development.
- Prefer small, focused pull requests with a clear description.
- Match the existing style; `ruff` enforces formatting and imports.

## Reporting issues

Open an issue with steps to reproduce, expected vs actual behavior, and your
environment (OS, Python version, model provider).
