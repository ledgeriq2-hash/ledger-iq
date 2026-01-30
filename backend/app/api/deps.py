from __future__ import annotations

import uuid
from dataclasses import dataclass
import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings as _get_settings
from app.core.redis import get_user_tokens_version, is_token_revoked
from app.core.security import decode_token
from app.core.redis import (
    get_redis as _get_redis,
)
from app.database import get_db as _get_db
from app.models.user import User
from app.services import user_service

logger = logging.getLogger(__name__)


async def get_db() -> AsyncSession:
    async for session in _get_db():
        yield session


def get_settings():
    return _get_settings()


async def get_redis():
    return await _get_redis()


def _is_dev_runtime(settings) -> bool:
    env = str(getattr(settings, "environment", "development") or "development").strip().lower()
    return env == "development"


@dataclass(frozen=True, slots=True)
class DevUser:
    """
    Minimal request-scoped actor context for local/dev runtime.

    This replaces JWT-authenticated User resolution.
    """

    id: uuid.UUID | None
    tenant_id: uuid.UUID
    is_active: bool = True
    is_superuser: bool = True


async def _resolve_user_from_token(
    request: Request,
    session: AsyncSession,
    token: str,
    tenant_header: str,
) -> User:
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    token_type = payload.get("type")
    if token_type not in (None, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    sub = payload.get("sub")
    tenant_claim = payload.get("tenant_id")
    if not sub or not tenant_claim:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    try:
        user_id = uuid.UUID(str(sub))
        tenant_id = uuid.UUID(str(tenant_claim))
        tenant_header_id = uuid.UUID(str(tenant_header))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims") from exc

    if tenant_id != tenant_header_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")

    if await is_token_revoked(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    token_version_claim = int(payload.get("token_version") or 0)
    current_version = await get_user_tokens_version(user_id)
    if token_version_claim < current_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is no longer valid")

    user = await user_service.get_user(session, tenant_id, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    request.state.user_id = user.id
    request.state.tenant_id = tenant_id
    request.state.user = user
    return user


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
) -> User | DevUser:
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    settings = get_settings()
    if token:
        return await _resolve_user_from_token(request, session, token, x_tenant_id)

    if not _is_dev_runtime(settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")

    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Tenant-Id header") from exc

    actor_uuid: uuid.UUID | None = None
    if actor_id:
        try:
            actor_uuid = uuid.UUID(actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Actor-Id header") from exc

    request.state.tenant_id = tenant_uuid
    request.state.user_id = actor_uuid
    return DevUser(id=actor_uuid, tenant_id=tenant_uuid)


async def get_current_active_user(
    current_user: Annotated[User | DevUser, Depends(get_current_user)]
) -> User | DevUser:
    if not getattr(current_user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return current_user


async def get_current_tenant(
    request: Request,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
) -> uuid.UUID:
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Tenant-Id header") from exc
    request.state.tenant_id = tenant_uuid
    return tenant_uuid


__all__ = [
    "get_db",
    "get_settings",
    "get_redis",
    "DevUser",
    "User",
    "get_current_user",
    "get_current_active_user",
    "get_current_tenant",
]
