from __future__ import annotations

import uuid
from typing import Callable

from app.core.logging import set_actor_id, set_request_id, set_run_id, set_tenant_id, set_user_id


class RequestIdASGIMiddleware:
    """Attach/propagate X-Request-ID and seed logging ContextVars."""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        correlation_id = None
        for key, value in scope.get("headers", []):
            lower_key = key.lower()
            if lower_key == b"x-request-id":
                request_id = value.decode("utf-8", errors="ignore")
                break
            if lower_key == b"x-correlation-id":
                correlation_id = value.decode("utf-8", errors="ignore")
        if not request_id:
            request_id = correlation_id or uuid.uuid4().hex

        set_request_id(request_id)
        set_user_id(None)
        set_tenant_id(None)
        set_actor_id(None)
        set_run_id(None)

        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["request_id"] = request_id

        async def send_wrapper(message) -> None:
            if message.get("type") == "http.response.start":
                if isinstance(state, dict):
                    user_id = state.get("user_id")
                    if not user_id:
                        user = state.get("user")
                        user_id = getattr(user, "id", None)
                    if user_id:
                        set_user_id(user_id)
                headers = list(message.get("headers", []))
                header_names = {key.lower() for key, _ in headers}
                if b"x-request-id" not in header_names:
                    headers.append((b"x-request-id", request_id.encode("utf-8")))
                if correlation_id and b"x-correlation-id" not in header_names:
                    headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

class RequestIdMiddleware(RequestIdASGIMiddleware):
    """Backward-compatible alias for RequestIdASGIMiddleware."""


__all__ = ["RequestIdASGIMiddleware", "RequestIdMiddleware"]
