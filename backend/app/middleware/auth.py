from __future__ import annotations

import uuid
from collections.abc import Callable
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import set_user_id
from app.core.security import decode_token
from app.core.logging import request_id_ctx_var

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Extract JWT subject for tracing (not authorization) and attach to request.state.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token:
            try:
                payload = decode_token(token)
                request.state.token_payload = payload
                sub = payload.get("sub")
                tenant_id = payload.get("tenant_id")
                request.state.user_id = uuid.UUID(str(sub)) if sub else None
                request.state.tenant_id = uuid.UUID(str(tenant_id)) if tenant_id else None
                if request.state.user_id:
                    set_user_id(request.state.user_id)
            except Exception as exc:
                request.state.token_payload = None
                logger.warning(
                    "auth_context.decode_failed",
                    extra={
                        "request_id": getattr(request.state, "request_id", request_id_ctx_var.get()),
                        "path": request.url.path,
                        "reason": str(exc),
                    },
                )

        response = await call_next(request)
        return response


__all__ = ["AuthContextMiddleware"]
