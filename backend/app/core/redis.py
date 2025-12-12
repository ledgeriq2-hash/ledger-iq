from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from redis.asyncio import Redis, from_url

from app.config import get_settings

settings = get_settings()

_redis_client: Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """Return a singleton Redis client."""
    global _redis_client

    client = _redis_client
    if client is not None and getattr(client, "closed", False):
        client = None
        _redis_client = None

    if client is None:
        async with _redis_lock:
            if _redis_client is None or getattr(_redis_client, "closed", False):
                _redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        client = _redis_client

    if client is None:  # pragma: no cover - defensive fallback
        raise RuntimeError("Redis client could not be initialized")

    return client


async def set_value(key: str, value: Any, ex: int | None = None) -> bool:
    """Set a value with optional expiry (seconds)."""
    client = await get_redis()
    result = await client.set(key, value, ex=ex)
    return bool(result)


async def get_value(key: str) -> Optional[str]:
    """Get a value by key."""
    client = await get_redis()
    result = await client.get(key)
    return result


async def delete_value(key: str) -> bool:
    """Delete a key if it exists."""
    client = await get_redis()
    deleted = await client.delete(key)
    return deleted > 0


def _seconds_until(expires_at: datetime | None) -> int:
    if expires_at is None:
        return 0
    delta = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(delta, 0)


def _token_jti_key(jti: str) -> str:
    return f"token:{jti}"


def _user_tokens_version_key(user_id: uuid.UUID | str) -> str:
    return f"user:{user_id}:tokens_version"


def _password_reset_key(token: str) -> str:
    return f"password_reset:{token}"


async def store_token_jti(jti: str, expires_at: datetime | None) -> None:
    """Mark a token identifier as revoked until its expiry."""
    ttl = _seconds_until(expires_at)
    if ttl <= 0:
        return
    client = await get_redis()
    await client.set(_token_jti_key(jti), "revoked", ex=ttl)


async def is_token_revoked(jti: str | None) -> bool:
    """Check whether a token identifier has been revoked."""
    if not jti:
        return False
    client = await get_redis()
    return bool(await client.exists(_token_jti_key(jti)))


async def get_user_tokens_version(user_id: uuid.UUID | str) -> int:
    """Return the current token namespace version for the given user."""
    client = await get_redis()
    value = await client.get(_user_tokens_version_key(user_id))
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


async def bump_user_tokens_version(user_id: uuid.UUID | str) -> int:
    """Increment the token namespace version to invalidate existing tokens."""
    client = await get_redis()
    return int(await client.incr(_user_tokens_version_key(user_id)))


async def set_password_reset_token(token: str, user_id: uuid.UUID, tenant_id: uuid.UUID, expires_in: int) -> None:
    """
    Store a password reset token for a user in Redis.

    Production should pair this with an email delivery that sends the token to the user.
    """
    client = await get_redis()
    await client.set(
        _password_reset_key(token),
        f"{user_id}:{tenant_id}",
        ex=expires_in,
    )


async def pop_password_reset_token(token: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Resolve and consume a password reset token if it exists."""
    client = await get_redis()
    try:
        value = await client.getdel(_password_reset_key(token))
    except AttributeError:  # pragma: no cover - fallback for older redis commands
        value = await client.get(_password_reset_key(token))
        if value:
            await client.delete(_password_reset_key(token))
    if not value:
        return None
    try:
        user_id_str, tenant_id_str = str(value).split(":")
        return uuid.UUID(user_id_str), uuid.UUID(tenant_id_str)
    except ValueError:
        return None


__all__ = [
    "get_redis",
    "set_value",
    "get_value",
    "delete_value",
    "store_token_jti",
    "is_token_revoked",
    "get_user_tokens_version",
    "bump_user_tokens_version",
    "set_password_reset_token",
    "pop_password_reset_token",
]
