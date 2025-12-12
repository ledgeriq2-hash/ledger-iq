from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings as _get_settings
from app.core.redis import (
    get_redis as _get_redis,
    get_user_tokens_version,
    is_token_revoked,
)
from app.core.security import decode_token
from app.database import get_db as _get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncSession:
    async for session in _get_db():
        yield session


def get_settings():
    return _get_settings()


async def get_redis():
    return await _get_redis()


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    sub = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not sub or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = uuid.UUID(str(sub))
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims") from exc

    token_type = payload.get("type")
    if token_type not in (None, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    if await is_token_revoked(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    current_version = await get_user_tokens_version(user_id)
    token_version = int(payload.get("token_version") or 0)
    if token_version < current_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is no longer valid")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.tenant_id or user.tenant_id != tenant_uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch for user")
    request.state.user = user
    request.state.tenant_id = tenant_uuid
    request.state.token_payload = payload
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_current_tenant(
    request: Request,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> uuid.UUID:
    """
    Determine tenant from token or explicit header.
    Header overrides token when provided.
    """
    if x_tenant_id:
        try:
            return uuid.UUID(x_tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant header") from exc
    user = getattr(request.state, "user", None)
    if user and getattr(user, "tenant_id", None):
        return user.tenant_id
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return uuid.UUID(str(tenant_id))
        except Exception:
            pass
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required")


__all__ = [
    "get_db",
    "get_settings",
    "get_redis",
    "get_current_user",
    "get_current_active_user",
    "get_current_tenant",
    "oauth2_scheme",
]
