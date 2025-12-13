from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis, from_url

from app.config import get_settings

settings = get_settings()

_redis_client: Redis | None = None
_memory_redis: Any | None = None
_redis_lock = asyncio.Lock()


class _InMemoryRedis:
    """Minimal async Redis-like client used when Redis is disabled."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self.closed = False

    def _purge_if_expired(self, key: str) -> None:
        if key not in self._store:
            return
        _, expires_at = self._store[key]
        if expires_at is not None and expires_at < asyncio.get_event_loop().time():
            self._store.pop(key, None)

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        expires_at = None
        if ex is not None:
            expires_at = asyncio.get_event_loop().time() + ex
        self._store[key] = (value, expires_at)
        return True

    async def get(self, key: str) -> Any:
        self._purge_if_expired(key)
        if key not in self._store:
            return None
        return self._store[key][0]

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            self._purge_if_expired(key)
            if key in self._store:
                self._store.pop(key, None)
                deleted += 1
        return deleted

    async def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        current = self._store.get(key, ("0", None))[0]
        try:
            value = int(current)
        except (TypeError, ValueError):
            value = 0
        value += 1
        # Preserve existing expiry, if any
        expires_at = self._store.get(key, (None, None))[1]
        self._store[key] = (value, expires_at)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._purge_if_expired(key)
        if key not in self._store:
            return False
        self._store[key] = (self._store[key][0], asyncio.get_event_loop().time() + seconds)
        return True

    async def exists(self, key: str) -> int:
        self._purge_if_expired(key)
        return 1 if key in self._store else 0

    async def getdel(self, key: str) -> Any:
        value = await self.get(key)
        if key in self._store:
            self._store.pop(key, None)
        return value


async def get_redis() -> Redis:
    """Return a singleton Redis client."""
    global _redis_client

    if not settings.redis_enabled:
        global _memory_redis
        if _memory_redis is None or getattr(_memory_redis, "closed", False):
            _memory_redis = _InMemoryRedis()  # type: ignore[assignment]
        return _memory_redis  # type: ignore[return-value]

    client = _redis_client
    if client is not None and getattr(client, "closed", False):
        client = None
        _redis_client = None

    if client is None:
        async with _redis_lock:
            if _redis_client is None or getattr(_redis_client, "closed", False):
                try:
                    _redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
                except Exception:
                    # Fallback to in-memory client if Redis is unreachable during init
                    settings.redis_enabled = False
                    _memory_redis = _InMemoryRedis()  # type: ignore[assignment]
        client = _redis_client if settings.redis_enabled else _memory_redis

    if client is None:  # pragma: no cover - defensive fallback
        raise RuntimeError("Redis client could not be initialized")

    return client


async def set_value(key: str, value: Any, ex: int | None = None) -> bool:
    """Set a value with optional expiry (seconds)."""
    client = await get_redis()
    result = await client.set(key, value, ex=ex)
    return bool(result)


async def get_value(key: str) -> str | None:
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
    delta = int((expires_at - datetime.now(UTC)).total_seconds())
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
