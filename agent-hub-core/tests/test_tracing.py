"""Tests for structured logging and trace-id correlation."""
from __future__ import annotations

import io
import json
import logging

from agent_hub_core.tracing import JsonFormatter, get_logger, new_trace_id, trace_id_var


def _capture(logger: logging.Logger) -> io.StringIO:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return stream


def test_trace_id_present_in_log_context():
    trace_id_var.set("test-trace-123")
    logger = get_logger("test.tracing.context")
    stream = _capture(logger)

    logger.info("something happened")

    record = json.loads(stream.getvalue().strip())
    assert record["trace_id"] == "test-trace-123"
    assert record["message"] == "something happened"
    assert record["level"] == "INFO"
    assert record["logger"] == "test.tracing.context"


def test_extra_fields_appear_in_structured_output():
    trace_id_var.set("test-trace-456")
    logger = get_logger("test.tracing.extra")
    stream = _capture(logger)

    logger.info("stage done", extra={"stage": "execute", "attempt": 2, "elapsed_ms": 12.5})

    record = json.loads(stream.getvalue().strip())
    assert record["stage"] == "execute"
    assert record["attempt"] == 2
    assert record["elapsed_ms"] == 12.5
    assert record["trace_id"] == "test-trace-456"


def test_trace_id_is_null_when_context_unset():
    token = trace_id_var.set(None)
    try:
        logger = get_logger("test.tracing.unset")
        stream = _capture(logger)

        logger.info("no trace context")

        record = json.loads(stream.getvalue().strip())
        assert "trace_id" in record
        assert record["trace_id"] is None
    finally:
        trace_id_var.reset(token)


def test_new_trace_id_is_unique_and_nonempty():
    a, b = new_trace_id(), new_trace_id()
    assert a and b and a != b


def test_get_logger_emits_json_lines_without_duplicate_handlers():
    logger_a = get_logger("test.tracing.dedupe")
    logger_b = get_logger("test.tracing.dedupe")
    assert logger_a is logger_b
    json_handlers = [
        h for h in logger_a.handlers
        if isinstance(getattr(h, "formatter", None), JsonFormatter)
    ]
    assert len(json_handlers) == 1
