import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace

from app.config import settings

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per line and correlate it with the active span."""

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service_name": settings.otel_service_name,
            "environment": settings.environment,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }

        if span_context.is_valid:
            payload["trace_id"] = format(span_context.trace_id, "032x")
            payload["span_id"] = format(span_context.span_id, "016x")
            payload["trace_flags"] = int(span_context.trace_flags)

        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(stdout_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "sqlalchemy.engine"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("opentelemetry.exporter").setLevel(logging.WARNING)
    logging.getLogger("grpc").setLevel(logging.WARNING)
