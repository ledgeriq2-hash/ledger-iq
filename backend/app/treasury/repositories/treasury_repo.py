from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.treasury import Treasury
from app.models.treasury_transaction import TreasuryTransaction


@dataclass(slots=True)
class TreasuryRepository:
    session: AsyncSession

    async def get_default_treasury_id(self, *, tenant_id: UUID) -> UUID | None:
        result = await self.session.execute(
            select(Treasury.id)
            .where(Treasury.tenant_id == tenant_id)
            .order_by(Treasury.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_transaction(
        self,
        *,
        tenant_id: UUID,
        treasury_id: UUID,
        amount: Decimal,
        direction: str,
        reference_type: str,
        reference_id: UUID,
        journal_entry_id: UUID,
        movement_type: str,
        party_type: str | None = None,
        party_id: UUID | None = None,
        reversed_of_id: UUID | None = None,
        is_reversed: bool = False,
        is_voided: bool = False,
        voided_at: datetime | None = None,
        voided_by_user_id: UUID | None = None,
        voided_reason: str | None = None,
    ) -> TreasuryTransaction:
        tx = TreasuryTransaction(
            tenant_id=tenant_id,
            treasury_id=treasury_id,
            amount=amount,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
            journal_entry_id=journal_entry_id,
            movement_type=movement_type,
            reversed_of_id=reversed_of_id,
            is_reversed=is_reversed,
            is_voided=is_voided,
            voided_at=voided_at,
            voided_by_user_id=voided_by_user_id,
            voided_reason=voided_reason,
        )
        if party_type and party_id:
            normalized = str(party_type).lower()
            if normalized == "client":
                tx.customer_id = party_id
            elif normalized == "supplier":
                tx.supplier_id = party_id
            elif normalized in {"worker", "employee"}:
                tx.employee_id = party_id
        tx.movement_type = movement_type
        self.session.add(tx)
        await self.session.flush()
        return tx


__all__ = ["TreasuryRepository"]
