"""Structured (JSON) logging with per-request trace correlation.

Every log line is a single JSON object written to stdout, so output is
container/log-aggregator friendly. A trace id is carried in a ContextVar:
the API middleware sets it per request (accepting an upstream X-Trace-Id
from a JARVIS orchestrator, or generating a fresh UUID), and every log call
made anywhere in that request's call stack picks it up automatically.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid

TRACE_HEADER = "X-Trace-Id"

trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)

# Attributes present on every LogRecord; anything else was passed via `extra`
# and belongs in the structured payload.
_STANDARD_RECORD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()
) | {"message", "asctime", "taskName"}


def new_trace_id() -> str:
    return uuid.uuid4().hex


class JsonFormatter(logging.Formatter):
    """Formats each record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger emitting structured JSON to stdout.

    Idempotent: calling twice with the same name does not stack handlers.
    """
    logger = logging.getLogger(name)
    has_json_handler = any(
        isinstance(getattr(handler, "formatter", None), JsonFormatter)
        for handler in logger.handlers
    )
    if not has_json_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
