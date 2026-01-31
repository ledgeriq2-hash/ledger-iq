from __future__ import annotations

import logging
import time
from typing import Final

from fastapi import Request, status

from app.core.exceptions import AppException
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

PUBLIC_RATE_LIMIT: Final[int] = 20
PUBLIC_LIMITED_ROUTES: Final[dict[str, str]] = {
    "summary": r"^/(?:api/)?(?:v1/)?portal/[^/]+/summary/?$",
    "invoices": r"^/(?:api/)?(?:v1/)?portal/[^/]+/invoices/?$",
    "statement": r"^/(?:api/)?(?:v1/)?portal/[^/]+/statement/?$",
}


def _route_id(path: str) -> str | None:
    import re

    normalized = (path or "").lower()
    for name, pattern in PUBLIC_LIMITED_ROUTES.items():
        if re.match(pattern, normalized):
            return name
    return None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int = 60) -> None:
    """
    Fixed-window rate limiter for sensitive public routes.
    """
    path = request.url.path or ""
    route_id = _route_id(path)
    if not route_id:
        return

    effective_limit = min(limit, PUBLIC_RATE_LIMIT)
    window = int(time.time() // window_seconds)
    client_ip = _client_ip(request)
    key = f"rate:{scope}:{route_id}:{client_ip}:{window}"

    try:
        redis = await get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > effective_limit:
            retry_after = max(1, window_seconds - (int(time.time()) % window_seconds))
            raise AppException(
                code="rate_limited",
                message="Too many requests",
                details={
                    "limit": effective_limit,
                    "window_seconds": window_seconds,
                    "route": route_id,
                },
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )
    except AppException:
        raise
    except Exception as exc:  # pragma: no cover - fail open
        logger.warning("rate_limit_failed", extra={"reason": str(exc), "path": path})
        return


__all__ = ["enforce_rate_limit"]
