from __future__ import annotations

import json
import uuid
from typing import Callable

from app.core.logging import set_actor_id, set_request_id, set_run_id, set_tenant_id, set_user_id
from app.shared.errors import error_shape


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

        response_started = False
        override_body: bytes | None = None

        async def send_wrapper(message) -> None:
            nonlocal response_started, override_body
            message_type = message.get("type")
            if message_type == "http.response.start":
                response_started = True
                if isinstance(state, dict):
                    user_id = state.get("user_id")
                    if not user_id:
                        user = state.get("user")
                        user_id = getattr(user, "id", None)
                    if user_id:
                        set_user_id(user_id)
                headers = list(message.get("headers", []))
                header_map = {key.lower(): value for key, value in headers}
                status = message.get("status")
                content_type = header_map.get(b"content-type", b"").decode("utf-8", errors="ignore")
                if status == 500 and not content_type.startswith("application/json"):
                    override_body = json.dumps(
                        error_shape(
                            code="internal_error",
                            message="Internal server error",
                            details=None,
                            request_id=request_id,
                        )
                    ).encode("utf-8")
                    filtered = [
                        (key, value)
                        for key, value in headers
                        if key.lower() not in {b"content-type", b"content-length", b"x-request-id", b"x-correlation-id"}
                    ]
                    response_headers = filtered + [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(override_body)).encode("utf-8")),
                        (b"x-request-id", request_id.encode("utf-8")),
                    ]
                    if correlation_id:
                        response_headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 500,
                            "headers": response_headers,
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": override_body,
                        }
                    )
                    return

                header_names = {key.lower() for key, _ in headers}
                if b"x-request-id" not in header_names:
                    headers.append((b"x-request-id", request_id.encode("utf-8")))
                if correlation_id and b"x-correlation-id" not in header_names:
                    headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                message["headers"] = headers
                await send(message)
                return
            if message_type == "http.response.body" and override_body is not None:
                return
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            if response_started:
                raise
            body = json.dumps(
                error_shape(
                    code="internal_error",
                    message="Internal server error",
                    details=None,
                    request_id=request_id,
                )
            ).encode("utf-8")
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("utf-8")),
                (b"x-request-id", request_id.encode("utf-8")),
            ]
            if correlation_id:
                headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": headers,
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )

class RequestIdMiddleware(RequestIdASGIMiddleware):
    """Backward-compatible alias for RequestIdASGIMiddleware."""


__all__ = ["RequestIdASGIMiddleware", "RequestIdMiddleware"]
