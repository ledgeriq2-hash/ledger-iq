from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any


request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_id(request_id: str | None) -> None:
    request_id_ctx_var.set(request_id)


def set_user_id(user_id: Any | None) -> None:
    user_id_ctx_var.set(str(user_id) if user_id else None)


class ContextFilter(logging.Filter):
    """Attach request/user context from ContextVars to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        record.user_id = user_id_ctx_var.get()
        return True


class JsonLogFormatter(logging.Formatter):
    """Format logs as JSON with request/user context."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None)
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id,
            "correlation_id": request_id,
            "user_id": getattr(record, "user_id", None),
        }

        if hasattr(record, "tenant_id"):
            payload["tenant_id"] = getattr(record, "tenant_id")
        if hasattr(record, "tenant_slug"):
            payload["tenant_slug"] = getattr(record, "tenant_slug")
        if hasattr(record, "soft_launch"):
            payload["soft_launch"] = getattr(record, "soft_launch")

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


def init_logging(debug: bool | None = None) -> None:
    """
    Initialize application-wide structured logging.

    Safe to call multiple times; handlers are reset on each invocation.
    """
    level = logging.DEBUG if debug else logging.INFO

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(level)
        logger.propagate = True

    logging.captureWarnings(True)


__all__ = [
    "init_logging",
    "JsonLogFormatter",
    "request_id_ctx_var",
    "user_id_ctx_var",
    "set_request_id",
    "set_user_id",
]
