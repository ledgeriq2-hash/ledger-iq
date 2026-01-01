from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.treasury_transaction import TreasuryTransaction


@dataclass(slots=True)
class TreasuryReportRepository:
    session: AsyncSession

    async def list_transactions(
        self,
        *,
        tenant_id: UUID,
        from_date: date | None,
        to_date: date | None,
        treasury_id: UUID | None,
        direction: str | None,
        reference_type: str | None,
        reference_id: UUID | None,
    ) -> list[dict]:
        query = (
            select(
                TreasuryTransaction.id,
                TreasuryTransaction.treasury_id,
                TreasuryTransaction.journal_entry_id,
                TreasuryTransaction.movement_type,
                TreasuryTransaction.amount,
                TreasuryTransaction.direction,
                TreasuryTransaction.reference_type,
                TreasuryTransaction.reference_id,
                TreasuryTransaction.customer_id,
                TreasuryTransaction.supplier_id,
                TreasuryTransaction.employee_id,
                TreasuryTransaction.created_at,
            )
            .select_from(TreasuryTransaction)
            .where(TreasuryTransaction.tenant_id == tenant_id)
        )

        if treasury_id:
            query = query.where(TreasuryTransaction.treasury_id == treasury_id)
        if direction:
            query = query.where(TreasuryTransaction.direction == direction)
        if reference_type:
            query = query.where(TreasuryTransaction.reference_type == reference_type)
        if reference_id:
            query = query.where(TreasuryTransaction.reference_id == reference_id)
        if from_date:
            query = query.where(func.date(TreasuryTransaction.created_at) >= from_date)
        if to_date:
            query = query.where(func.date(TreasuryTransaction.created_at) <= to_date)

        query = query.order_by(TreasuryTransaction.created_at.desc())
        result = await self.session.execute(query)
        rows: list[dict] = []
        for r in result.all():
            rows.append(
                {
                    "id": r[0],
                    "treasury_id": r[1],
                    "journal_entry_id": r[2],
                    "movement_type": r[3],
                    "amount": Decimal(str(r[4] or 0)).quantize(Decimal("0.01")),
                    "direction": r[5],
                    "reference_type": r[6],
                    "reference_id": r[7],
                    "customer_id": r[8],
                    "supplier_id": r[9],
                    "employee_id": r[10],
                    "created_at": r[11],
                }
            )
        return rows


__all__ = ["TreasuryReportRepository"]
