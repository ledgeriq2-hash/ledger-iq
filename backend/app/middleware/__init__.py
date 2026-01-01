from __future__ import annotations

from fastapi import FastAPI

from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.identity_context import IdentityContextMiddleware
from app.middleware.tenant import TenantMiddleware


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(IdentityContextMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLoggingMiddleware)


__all__ = [
    "register_middlewares",
    "TenantMiddleware",
    "RequestLoggingMiddleware",
    "RequestIdMiddleware",
    "IdentityContextMiddleware",
]
