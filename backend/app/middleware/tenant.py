from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import json_error_response
from app.core.logging import set_actor_id, set_tenant_id, set_user_id


class TenantMiddleware(BaseHTTPMiddleware):
    """Require dev headers and attach tenant/actor context to request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = (request.url.path or "").lower()
        is_api_path = path.startswith("/api/")
        is_portal_public = path.startswith("/api/v1/portal/") and not path.startswith("/api/v1/portal/link")
        is_exempt = path.startswith("/health") or path.startswith("/metrics") or path in {
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
            "/api/v1/dev/tenants",
            "/api/v1/dev/runs/lineage",
        }

        if is_api_path and not is_exempt and not is_portal_public:
            tenant_header = request.headers.get("X-Tenant-Id")
            if not tenant_header:
                return json_error_response(
                status.HTTP_400_BAD_REQUEST,
                "tenant_required",
                "X-Tenant-Id header required",
            )
            try:
                request.state.tenant_id = uuid.UUID(tenant_header)
            except ValueError:
                return json_error_response(
                    status.HTTP_400_BAD_REQUEST,
                    "tenant_invalid",
                    "Invalid X-Tenant-Id header",
                )
            set_tenant_id(request.state.tenant_id)

            actor_header = request.headers.get("X-Actor-Id")
            if actor_header:
                try:
                    request.state.user_id = uuid.UUID(actor_header)
                except ValueError:
                    return json_error_response(
                        status.HTTP_400_BAD_REQUEST,
                        "actor_invalid",
                        "Invalid X-Actor-Id header",
                    )
            else:
                request.state.user_id = None

            set_user_id(request.state.user_id)
            set_actor_id(request.state.user_id)

        response = await call_next(request)
        return response


__all__ = ["TenantMiddleware"]
