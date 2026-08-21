"""Structured logging configuration with correlation ID tracking."""

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Context variable to hold the active request correlation ID across async tasks
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


class StructuredJsonFormatter(logging.Formatter):
    """Custom JSON formatter injecting correlation_id, timestamp, and context."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        correlation_id = correlation_id_ctx.get()

        log_data: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if correlation_id:
            log_data["correlation_id"] = correlation_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if present
        extra_data = getattr(record, "extra", None)
        if isinstance(extra_data, dict):
            log_data.update(extra_data)

        return json.dumps(log_data)


class CorrelationIdFilter(logging.Filter):
    """Logging filter to inject correlation ID into standard log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get() or "-"
        return True


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """Configure root and application loggers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)

    if json_format:
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        log_format = "%(asctime)s [%(levelname)s] [req:%(correlation_id)s] %(name)s: %(message)s"
        formatter = logging.Formatter(log_format)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(CorrelationIdFilter())

    root_logger.addHandler(stream_handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with the given name."""
    return logging.getLogger(name)
