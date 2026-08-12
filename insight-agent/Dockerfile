FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY insight_agent ./insight_agent
COPY frontend ./frontend
COPY sample_data ./sample_data

RUN pip install --upgrade pip && pip install ".[anthropic,ollama]"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

CMD ["uvicorn", "insight_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
