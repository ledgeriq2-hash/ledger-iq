from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.use_cases.generate_party_statement import generate_party_statement


async def generate_client_statement(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    client_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    return await generate_party_statement(
        session,
        tenant_id=tenant_id,
        entity_type="client",
        entity_id=client_id,
        from_date=from_date,
        to_date=to_date,
    )


__all__ = ["generate_client_statement"]
