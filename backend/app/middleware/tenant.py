from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import set_user_id


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant ID from header or token payload into request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id_header = request.headers.get("X-Tenant-ID")
        tenant_id = None
        if tenant_id_header:
            try:
                tenant_id = uuid.UUID(tenant_id_header)
            except ValueError:
                tenant_id = None

        if tenant_id is None:
            token_payload = getattr(request.state, "token_payload", {}) or {}
            token_tid = token_payload.get("tenant_id")
            if token_tid:
                try:
                    tenant_id = uuid.UUID(str(token_tid))
                except ValueError:
                    tenant_id = None

        if tenant_id:
            request.state.tenant_id = tenant_id

        user_id = getattr(request.state, "user_id", None)
        if user_id:
            set_user_id(user_id)

        response = await call_next(request)
        return response


__all__ = ["TenantMiddleware"]
