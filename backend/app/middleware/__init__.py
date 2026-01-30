from __future__ import annotations

from fastapi import FastAPI

from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.tenant import TenantMiddleware

try:
    from app.middleware.identity_context import IdentityContextMiddleware
except Exception:
    IdentityContextMiddleware = None


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(TenantMiddleware)
    if IdentityContextMiddleware is not None:
        app.add_middleware(IdentityContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)


__all__ = [
    "register_middlewares",
    "TenantMiddleware",
    "RequestLoggingMiddleware",
    "RequestIdMiddleware",
    "IdentityContextMiddleware",
]
