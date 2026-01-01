from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.core.logging import request_id_ctx_var
from app.database import async_session_maker
from app.shared.errors import error_shape
from app.services import error_event_service

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Any = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.http_status = http_status
        super().__init__(message)


def _error_payload(code: str, message: str, details: Any = None, request_id: str | None = None) -> dict[str, Any]:
    return error_shape(code=code, message=message, details=details, request_id=request_id)


def json_error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    request_id = request_id_ctx_var.get()
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=_error_payload(code, message, details, request_id),
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Exception):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return [_jsonable(v) for v in value]
    return value


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return json_error_response(exc.http_status, exc.code, exc.message, exc.details)


async def validation_exception_handler(request: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    details = None
    if isinstance(exc, RequestValidationError):
        details = exc.errors()
    elif isinstance(exc, ValidationError):
        details = exc.errors()

    if details is not None:
        details = _jsonable(details)

    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    if path.startswith("/api/v1/ml/") and details:
        def loc_last(err: dict) -> str | None:
            loc = err.get("loc")
            if isinstance(loc, (list, tuple)) and loc:
                return str(loc[-1])
            return None

        fields = {loc_last(err) for err in details if isinstance(err, dict)}
        if "prediction_type" in fields:
            return json_error_response(status.HTTP_400_BAD_REQUEST, "invalid_prediction_type", "Invalid prediction_type.", details)
        if "model_version" in fields:
            return json_error_response(status.HTTP_400_BAD_REQUEST, "invalid_model_version", "Invalid model_version.", details)
        if "granularity" in fields:
            return json_error_response(status.HTTP_400_BAD_REQUEST, "invalid_granularity", "Invalid granularity.", details)

    return json_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", "Validation error", details)


async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
    return json_error_response(status.HTTP_409_CONFLICT, "integrity_error", "Integrity error", message)


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    status_code = exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = "unauthorized" if status_code == status.HTTP_401_UNAUTHORIZED else (
        "forbidden" if status_code == status.HTTP_403_FORBIDDEN else "http_error"
    )
    return json_error_response(status_code, code, detail, exc.detail if not isinstance(exc.detail, str) else None)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id_ctx_var.get()},
    )
    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None) or getattr(getattr(request.state, "user", None), "id", None)
        async with async_session_maker() as session:
            await error_event_service.record_error_event(
                session,
                tenant_id=tenant_id,
                user_id=user_id,
                path=str(request.url.path),
                method=request.method,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_message=str(exc),
            )
        try:
            request.state.error_event_recorded = True
        except Exception:
            pass
    except Exception as logging_exc:
        # Avoid masking the original error path; logging already captured.
        logger.warning(
            "error_event_record_failed",
            extra={
                "request_id": request_id_ctx_var.get(),
                "reason": str(logging_exc),
            },
        )
    return json_error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "Internal server error", None)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]


__all__ = ["AppException", "register_exception_handlers", "json_error_response"]
