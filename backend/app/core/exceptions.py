from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.database import async_session_maker
from app.services import error_event_service

from app.core.logging import request_id_ctx_var

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _error_payload(code: str, message: str) -> dict[str, Any]:
    request_id = request_id_ctx_var.get()
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": request_id,
    }


def _json_response(status_code: int, code: str, message: str) -> JSONResponse:
    request_id = request_id_ctx_var.get()
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=_error_payload(code, message),
    )


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        headers={"X-Request-ID": request_id_ctx_var.get()} if request_id_ctx_var.get() else None,
        content=_error_payload(exc.code, exc.message),
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    return _json_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", str(exc))


async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
    return _json_response(status.HTTP_409_CONFLICT, "integrity_error", message)


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
    except Exception:
        # Avoid masking the original error path; logging already captured.
        pass
    return _json_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


__all__ = ["AppException", "register_exception_handlers"]
