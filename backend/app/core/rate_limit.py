from __future__ import annotations

import ipaddress

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.core.redis import get_redis

settings = get_settings()


def _client_key(request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    try:
        ip_obj = ipaddress.ip_address(client)
        return ip_obj.exploded
    except Exception:
        return client


async def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int = 60) -> None:
    """
    Very small Redis-based rate limiter.

    Key is derived from client IP + scope. When limit is zero or negative, limiter is disabled.
    """
    if not settings.redis_enabled or limit is None or limit <= 0:
        return
    redis = await get_redis()
    key = f"rl:{scope}:{_client_key(request)}"
    count = await redis.incr(key)
    if count == 1:
        # best-effort expiry; ignore failures
        try:
            await redis.expire(key, window_seconds)
        except Exception:
            pass
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )


__all__ = ["enforce_rate_limit"]
