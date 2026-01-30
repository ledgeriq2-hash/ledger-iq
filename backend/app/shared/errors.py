from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorObject(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorObject
    request_id: str | None = None


class ErrorDetail(ErrorObject):
    """Backward-compatible alias for ErrorObject."""


class ErrorResponse(ErrorEnvelope):
    """Backward-compatible alias for ErrorEnvelope."""


def error_shape(
    *,
    code: str,
    message: str,
    details: Any | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "request_id": request_id,
    }


__all__ = [
    "ErrorObject",
    "ErrorEnvelope",
    "ErrorResponse",
    "ErrorDetail",
    "error_shape",
]
