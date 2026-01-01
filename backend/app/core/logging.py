from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx_var: ContextVar[str | None] = ContextVar("user_id", default=None)
tenant_id_ctx_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
actor_id_ctx_var: ContextVar[str | None] = ContextVar("actor_id", default=None)
run_id_ctx_var: ContextVar[str | None] = ContextVar("run_id", default=None)


def set_request_id(request_id: str | None) -> None:
    request_id_ctx_var.set(request_id)


def set_user_id(user_id: Any | None) -> None:
    user_id_ctx_var.set(str(user_id) if user_id else None)


def set_tenant_id(tenant_id: Any | None) -> None:
    tenant_id_ctx_var.set(str(tenant_id) if tenant_id else None)


def set_actor_id(actor_id: Any | None) -> None:
    actor_id_ctx_var.set(str(actor_id) if actor_id else None)


def set_run_id(run_id: Any | None) -> None:
    run_id_ctx_var.set(str(run_id) if run_id else None)


class ContextFilter(logging.Filter):
    """Attach request/user context from ContextVars to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        record.user_id = user_id_ctx_var.get()
        record.tenant_id = tenant_id_ctx_var.get()
        record.actor_id = actor_id_ctx_var.get()
        record.run_id = run_id_ctx_var.get()
        return True


class JsonLogFormatter(logging.Formatter):
    """Format logs as JSON with request/user context."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None)
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id,
            "correlation_id": request_id,
            "user_id": getattr(record, "user_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
            "actor_id": getattr(record, "actor_id", None),
            "run_id": getattr(record, "run_id", None),
        }

        for key in (
            "tenant_slug",
            "soft_launch",
            "method",
            "path",
            "query",
            "status_code",
            "duration_ms",
            "prediction_type",
            "model_version",
            "data_snapshot_id",
            "snapshot_id",
            "content_hash",
            "endpoint",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def _log_level(debug: bool | None = None, log_level: str | None = None) -> int:
    if debug:
        return logging.DEBUG
    name = str(log_level or "INFO").upper()
    resolved = logging.getLevelName(name)
    return resolved if isinstance(resolved, int) else logging.INFO


def init_logging(debug: bool | None = None, log_level: str | None = None) -> None:
    """
    Initialize application-wide structured logging.

    Safe to call multiple times; handlers are reset on each invocation.
    """
    level = _log_level(debug, log_level)

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
    "tenant_id_ctx_var",
    "actor_id_ctx_var",
    "run_id_ctx_var",
    "set_request_id",
    "set_user_id",
    "set_tenant_id",
    "set_actor_id",
    "set_run_id",
]
