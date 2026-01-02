from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.accounting.repositories.statement_repo import StatementRepository


async def generate_party_statement(
    session,
    *,
    tenant_id: UUID,
    entity_type: str,
    entity_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    repo = StatementRepository(session=session)
    opening_balance = Decimal("0.00")
    if from_date:
        opening_balance = await repo.get_entity_opening_balance(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            before_date=from_date,
        )

    lines = await repo.list_entity_lines(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
    )

    running = opening_balance
    out_lines: list[dict] = []
    for line in lines:
        running += (Decimal(str(line["debit"] or 0)) - Decimal(str(line["credit"] or 0))).quantize(Decimal("0.01"))
        out_lines.append({**line, "running_balance": running})

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "period": {"from_date": from_date, "to_date": to_date},
        "opening_balance": opening_balance,
        "closing_balance": running,
        "lines": out_lines,
    }


async def generate_supplier_statement(
    session,
    *,
    tenant_id: UUID,
    supplier_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    return await generate_party_statement(
        session,
        tenant_id=tenant_id,
        entity_type="supplier",
        entity_id=supplier_id,
        from_date=from_date,
        to_date=to_date,
    )


async def generate_employee_statement(
    session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    return await generate_party_statement(
        session,
        tenant_id=tenant_id,
        entity_type="worker",
        entity_id=employee_id,
        from_date=from_date,
        to_date=to_date,
    )


__all__ = [
    "generate_party_statement",
    "generate_supplier_statement",
    "generate_employee_statement",
]
