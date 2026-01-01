from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.treasury.repositories.treasury_report_repo import TreasuryReportRepository


async def generate_treasury_report(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    treasury_id: UUID | None = None,
    direction: str | None = None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
) -> dict:
    repo = TreasuryReportRepository(session=session)
    transactions = await repo.list_transactions(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        treasury_id=treasury_id,
        direction=direction,
        reference_type=reference_type,
        reference_id=reference_id,
    )

    total_in = Decimal("0.00")
    total_out = Decimal("0.00")
    for tx in transactions:
        if tx.get("direction") == "in":
            total_in += Decimal(str(tx.get("amount") or 0))
        elif tx.get("direction") == "out":
            total_out += Decimal(str(tx.get("amount") or 0))

    return {
        "period": {"from_date": from_date, "to_date": to_date},
        "filters": {
            "treasury_id": treasury_id,
            "direction": direction,
            "reference_type": reference_type,
            "reference_id": reference_id,
        },
        "totals": {
            "in": total_in.quantize(Decimal("0.01")),
            "out": total_out.quantize(Decimal("0.01")),
            "net": (total_in - total_out).quantize(Decimal("0.01")),
        },
        "transactions": transactions,
    }


__all__ = ["generate_treasury_report"]

