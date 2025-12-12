from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password, enforce_password_policy
from app.models.refresh_token import RefreshToken
from app.models.user import User


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_users(session: AsyncSession, tenant_id: UUID) -> Sequence[User]:
    result = await session.execute(select(User).where(User.tenant_id == tenant_id))
    return result.scalars().all()


async def get_user(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, tenant_id: UUID, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email, User.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _apply_password(data: dict[str, Any]) -> dict[str, Any]:
    if "password" in data:
        password = data.pop("password")
        if password:
            enforce_password_policy(password)
            data["hashed_password"] = get_password_hash(password)
    return data


async def create_user(session: AsyncSession, tenant_id: UUID, payload: Any) -> User:
    data = _apply_password(_to_dict(payload))
    user = User(**data, tenant_id=tenant_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, tenant_id: UUID, user_id: UUID, payload: Any) -> User | None:
    user = await get_user(session, tenant_id, user_id)
    if not user:
        return None
    data = _apply_password(_to_dict(payload, exclude_unset=True))
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> bool:
    result = await session.execute(delete(User).where(User.id == user_id, User.tenant_id == tenant_id))
    await session.commit()
    return result.rowcount > 0


async def authenticate_user(session: AsyncSession, tenant_id: UUID, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, tenant_id, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def set_last_login(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> None:
    user = await get_user(session, tenant_id, user_id)
    if not user:
        return
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def store_refresh_token(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    refresh_token: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshToken:
    token = RefreshToken(
        token_hash=_hash_token(refresh_token),
        user_id=user_id,
        tenant_id=tenant_id,
        expires_at=expires_at,
        revoked=False,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def get_valid_refresh_token(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, refresh_token: str, now: datetime | None = None
) -> RefreshToken | None:
    now = now or datetime.now(timezone.utc)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hash_token(refresh_token),
            RefreshToken.tenant_id == tenant_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(
    session: AsyncSession, tenant_id: UUID, refresh_token: str, user_id: UUID | None = None
) -> bool:
    conditions = [
        RefreshToken.token_hash == _hash_token(refresh_token),
        RefreshToken.tenant_id == tenant_id,
    ]
    if user_id:
        conditions.append(RefreshToken.user_id == user_id)
    result = await session.execute(select(RefreshToken).where(*conditions))
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.revoked = True
    await session.commit()
    return True


async def revoke_all_refresh_tokens_for_user(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> int:
    result = await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.tenant_id == tenant_id,
            RefreshToken.revoked.is_(False),
        )
        .values(revoked=True)
        .returning(RefreshToken.id)
    )
    await session.commit()
    rows = result.fetchall()
    return len(rows)


async def update_user_password(session: AsyncSession, tenant_id: UUID, user_id: UUID, new_password: str) -> User | None:
    user = await get_user(session, tenant_id, user_id)
    if not user:
        return None
    user.hashed_password = get_password_hash(new_password)
    await session.commit()
    await session.refresh(user)
    return user


__all__ = [
    "list_users",
    "get_user",
    "get_user_by_email",
    "create_user",
    "update_user",
    "delete_user",
    "authenticate_user",
    "set_last_login",
    "store_refresh_token",
    "get_valid_refresh_token",
    "revoke_refresh_token",
    "revoke_all_refresh_tokens_for_user",
    "update_user_password",
]
