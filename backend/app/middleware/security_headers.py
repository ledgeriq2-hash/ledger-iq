from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative security headers to all responses."""

    def __init__(self, app, settings):
        super().__init__(app)
        self.settings = settings

    def _is_production(self) -> bool:
        env = str(getattr(self.settings, "environment", "production") or "production").strip().lower()
        return env in {"production", "prod"}

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(),"
            " midi=(), payment=(), usb=(), fullscreen=(), display-capture=()",
        )
        if self._is_production():
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        return response


__all__ = ["SecurityHeadersMiddleware"]
