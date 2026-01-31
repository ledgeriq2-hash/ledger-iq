from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import deps
from app.core.exceptions import json_error_response
from app.core.logging import set_actor_id, set_tenant_id, set_user_id
from app.database import async_session_maker
from app.services import user_service

TENANT_REQUIRED_HINT = "Select a company (tenant) or create a demo company"


class TenantMiddleware(BaseHTTPMiddleware):
    """Require dev headers and attach tenant/actor context to request.state."""

    async def _infer_tenant_id(self, request: Request) -> uuid.UUID | None:
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None

        async with async_session_maker() as session:
            user = await deps._resolve_user_from_token(request, session, token, None)
            tenant_ids = await user_service.list_accessible_tenant_ids(session, user, limit=2)
        if len(tenant_ids) == 1:
            return tenant_ids[0]
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = (request.url.path or "").lower()
        is_api_path = path.startswith("/api/")
        portal_prefix = "/api/v1/portal/"
        is_portal_public = False
        if path.startswith(portal_prefix):
            suffix = path[len(portal_prefix):]
            parts = [part for part in suffix.split("/") if part]
            if len(parts) == 2 and parts[1] in {"summary", "balance", "invoices", "payments", "statement"}:
                is_portal_public = True
        is_exempt = path.startswith("/health") or path.startswith("/metrics") or path in {
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
            "/api/v1/dev/tenants",
            "/api/v1/dev/runs/lineage",
            "/api/v1/dev/trigger-500",
            "/api/v1/dev/bootstrap",
        }

        if is_api_path and not is_exempt and not is_portal_public:
            tenant_header = request.headers.get("X-Tenant-Id")
            if not tenant_header:
                inferred_tenant_id = await self._infer_tenant_id(request)
                if not inferred_tenant_id:
                    return json_error_response(
                        status.HTTP_400_BAD_REQUEST,
                        "TENANT_REQUIRED",
                        "Tenant header is required",
                        {"hint": TENANT_REQUIRED_HINT},
                    )
                request.state.tenant_id = inferred_tenant_id
            else:
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
            elif not hasattr(request.state, "user_id"):
                request.state.user_id = None

            set_user_id(request.state.user_id)
            set_actor_id(request.state.user_id)

        response = await call_next(request)
        return response


__all__ = ["TenantMiddleware"]
