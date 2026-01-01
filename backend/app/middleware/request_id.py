from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import set_actor_id, set_request_id, set_run_id, set_tenant_id, set_user_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach/propagate X-Request-ID and seed logging ContextVars."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        set_user_id(None)
        set_tenant_id(None)
        set_actor_id(None)
        set_run_id(None)
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Capture user_id for any downstream logging after dependencies.
        user_id = getattr(request.state, "user_id", None) or getattr(getattr(request.state, "user", None), "id", None)
        if user_id:
            set_user_id(user_id)

        return response


__all__ = ["RequestIdMiddleware"]
