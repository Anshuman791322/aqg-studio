"""Structured logging configuration with correlation ID tracking and secret redaction."""

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# Context variable to hold the active request correlation ID across async tasks
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Regex patterns to sanitize sensitive credentials from logs
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{10,})", re.IGNORECASE),
    re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(nvapi-[a-zA-Z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(['\"]?password['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(['\"]?apiKey['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Sanitize tokens, API keys, and passwords from log strings."""
    if not text:
        return text
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Custom JSON formatter injecting correlation_id, timestamp, and sanitized context."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        correlation_id = correlation_id_ctx.get()

        raw_message = record.getMessage()
        sanitized_message = redact_secrets(raw_message)

        log_data: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": sanitized_message,
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
            # Redact string values in extra data dictionary
            safe_extra = {
                k: redact_secrets(str(v)) if isinstance(v, str) else v
                for k, v in extra_data.items()
            }
            log_data.update(safe_extra)

        return json.dumps(log_data)


class CorrelationIdFilter(logging.Filter):
    """Logging filter to inject correlation ID and sanitize log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get() or "-"
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        return True


def setup_logging(
    log_level: str = "INFO",
    json_format: bool | None = None,
    environment: str = "development",
) -> None:
    """Configure root and application loggers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)

    use_json = (
        json_format
        if json_format is not None
        else environment.lower() in ("production", "staging")
    )

    if use_json:
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
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with the given name."""
    return logging.getLogger(name)
