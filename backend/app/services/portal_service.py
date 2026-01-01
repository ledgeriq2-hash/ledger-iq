from __future__ import annotations

import hashlib
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portal_token import PortalEntityType, PortalToken


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def _create_portal_token(
    session: AsyncSession,
    tenant_id: UUID,
    entity_type: PortalEntityType,
    entity_id: UUID,
    expires_at: datetime,
    raw_token: str | None = None,
) -> tuple[str, PortalToken]:
    token_value = raw_token or secrets.token_urlsafe(32)
    token_hash = _hash_token(token_value)
    token = PortalToken(
        token_hash=token_hash,
        entity_type=entity_type,
        entity_id=entity_id,
        expires_at=expires_at,
        is_used=False,
        tenant_id=tenant_id,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token_value, token


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_portal_tokens(session: AsyncSession, tenant_id: UUID) -> Sequence[PortalToken]:
    result = await session.execute(select(PortalToken).where(PortalToken.tenant_id == tenant_id))
    return result.scalars().all()


async def get_portal_token(session: AsyncSession, tenant_id: UUID, token_id: UUID) -> PortalToken | None:
    result = await session.execute(
        select(PortalToken).where(PortalToken.id == token_id, PortalToken.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_portal_token_by_hash(
    session: AsyncSession, tenant_id: UUID, token_hash: str
) -> PortalToken | None:
    result = await session.execute(
        select(PortalToken).where(PortalToken.token_hash == token_hash, PortalToken.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_portal_token(session: AsyncSession, tenant_id: UUID, payload: Any) -> PortalToken:
    data = _to_dict(payload)
    token = PortalToken(**data, tenant_id=tenant_id)
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def create_portal_token_for_customer(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID, expires_at: datetime
) -> tuple[str, PortalToken]:
    return await _create_portal_token(
        session,
        tenant_id=tenant_id,
        entity_type=PortalEntityType.CUSTOMER,
        entity_id=customer_id,
        expires_at=expires_at,
    )


async def create_portal_token_for_supplier(
    session: AsyncSession, tenant_id: UUID, supplier_id: UUID, expires_at: datetime
) -> tuple[str, PortalToken]:
    return await _create_portal_token(
        session,
        tenant_id=tenant_id,
        entity_type=PortalEntityType.SUPPLIER,
        entity_id=supplier_id,
        expires_at=expires_at,
    )


async def mark_portal_token_used(
    session: AsyncSession,
    tenant_id: UUID | None,
    token_id: UUID,
    is_used: bool = True,
) -> PortalToken | None:
    if tenant_id:
        token = await get_portal_token(session, tenant_id, token_id)
    else:
        token = (await session.execute(select(PortalToken).where(PortalToken.id == token_id))).scalar_one_or_none()
    if not token:
        return None
    token.is_used = is_used
    await session.commit()
    await session.refresh(token)
    return token


async def delete_portal_token(session: AsyncSession, tenant_id: UUID, token_id: UUID) -> bool:
    result = await session.execute(
        delete(PortalToken).where(PortalToken.id == token_id, PortalToken.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


async def validate_portal_token(
    session: AsyncSession, token: str
) -> tuple[PortalEntityType, Any, PortalToken] | None:
    """
    Validate a portal token for customer/supplier access.

    Returns a tuple of (entity_type, entity_record, portal_token) when valid.
    """
    token_hash = _hash_token(token)
    result = await session.execute(select(PortalToken).where(PortalToken.token_hash == token_hash))
    portal_token = result.scalar_one_or_none()
    if not portal_token:
        return None
    expires_at = portal_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if expires_at <= now:
        return None
    if portal_token.is_used:
        return None

    entity = None
    if portal_token.entity_type == PortalEntityType.CUSTOMER:
        from app.services import customer_service

        entity = await customer_service.get_customer(session, portal_token.tenant_id, portal_token.entity_id)
    elif portal_token.entity_type == PortalEntityType.SUPPLIER:
        from app.services import supplier_service

        entity = await supplier_service.get_supplier(session, portal_token.tenant_id, portal_token.entity_id)
    if not entity:
        return None

    return portal_token.entity_type, entity, portal_token


__all__ = [
    "list_portal_tokens",
    "get_portal_token",
    "get_portal_token_by_hash",
    "create_portal_token",
    "create_portal_token_for_customer",
    "create_portal_token_for_supplier",
    "validate_portal_token",
    "mark_portal_token_used",
    "delete_portal_token",
]
