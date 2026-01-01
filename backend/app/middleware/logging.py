from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_ctx_var, user_id_ctx_var
from app.core.soft_launch import is_soft_launch_tenant
from app.database import async_session_maker
from app.metrics import SOFT_LAUNCH_REQUESTS
from app.services import error_event_service

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log incoming requests and responses with correlation IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        request_id = request_id_ctx_var.get()
        tenant_id = getattr(request.state, "tenant_id", None) or request.headers.get("X-Tenant-Id")
        tenant_slug = request.headers.get("X-Tenant-Slug")
        soft_launch = is_soft_launch_tenant(tenant_slug)
        user_id = user_id_ctx_var.get()

        logger.info(
            "request.start",
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "soft_launch": soft_launch,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
            },
        )

        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            status_code = response.status_code if response else 500
            if soft_launch:
                try:
                    SOFT_LAUNCH_REQUESTS.labels(path=request.url.path).inc()
                except Exception as exc:
                    logger.warning(
                        "soft_launch_metric_failed",
                        extra={
                            "request_id": request_id,
                            "path": request.url.path,
                            "reason": str(exc),
                        },
                    )
            logger.info(
                "request.complete",
                extra={
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "tenant_slug": tenant_slug,
                    "soft_launch": soft_launch,
                    "user_id": user_id_ctx_var.get(),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            if status_code >= 500 and not getattr(request.state, "error_event_recorded", False):
                try:
                    async with async_session_maker() as session:
                        await error_event_service.record_error_event(
                            session,
                            tenant_id=getattr(request.state, "tenant_id", None),
                            user_id=getattr(request.state, "user_id", None) or getattr(
                                getattr(request.state, "user", None), "id", None
                            ),
                            path=str(request.url.path),
                            method=request.method,
                            status_code=status_code,
                            error_message=f"HTTP {status_code}",
                        )
                    request.state.error_event_recorded = True
                except Exception as exc:
                    # Avoid masking request handling in case of logging persistence issues.
                    logger.warning(
                        "error_event_record_failed",
                        extra={
                            "request_id": request_id,
                            "path": request.url.path,
                            "status_code": status_code,
                            "reason": str(exc),
                        },
                    )


__all__ = ["RequestLoggingMiddleware"]
