from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics import EXPENSES_CREATED
from app.models.expense import Expense
from app.services import journal_service, stock_movement_service
from app.services.accounting_mapping import get_account_mapping


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def _load_expense_account_mapping(session: AsyncSession, tenant_id: UUID) -> dict[str, UUID | None]:
    mapping = await get_account_mapping(session, tenant_id)
    return {
        "expense": mapping.get("expense_account_id"),
        "cash": mapping.get("cash_account_id"),
        "payables": mapping.get("payables_account_id"),
    }


async def _post_expense_entry(session: AsyncSession, tenant_id: UUID, expense: Expense) -> None:
    mapping = await _load_expense_account_mapping(session, tenant_id)
    expense_account = mapping.get("expense")
    cash_or_payable = mapping.get("payables") or mapping.get("cash")
    if not expense_account or not cash_or_payable:
        return

    amount = Decimal(str(expense.amount or 0))
    if amount <= 0:
        return

    expense_date = expense.expense_date
    lines = [
        {
            "account_id": expense_account,
            "debit": amount,
            "credit": Decimal("0"),
            "line_description": f"Expense {expense.id}",
        },
        {
            "account_id": cash_or_payable,
            "debit": Decimal("0"),
            "credit": amount,
            "line_description": f"Expense {expense.id} funding",
        },
    ]
    await journal_service.create_journal_entry_with_lines(
        session=session,
        tenant_id=tenant_id,
        date=expense_date,
        description=f"Expense {expense.id} recognition",
        reference=str(expense.id),
        lines=lines,
    )


async def list_expenses(session: AsyncSession, tenant_id: UUID) -> Sequence[Expense]:
    result = await session.execute(select(Expense).where(Expense.tenant_id == tenant_id))
    return result.scalars().all()


async def get_expense(session: AsyncSession, tenant_id: UUID, expense_id: UUID) -> Expense | None:
    result = await session.execute(
        select(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_expense(session: AsyncSession, tenant_id: UUID, payload: Any) -> Expense:
    data = _to_dict(payload)
    product_id = data.pop("product_id", None)
    quantity = data.pop("quantity", None)
    expense = Expense(**data, tenant_id=tenant_id)
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    try:
        EXPENSES_CREATED.labels(tenant_id=str(tenant_id)).inc()
    except Exception:
        pass
    if product_id and quantity:
        await stock_movement_service.create_movement(
            session,
            tenant_id,
            {
                "product_id": product_id,
                "quantity": quantity,
                "movement_type": stock_movement_service.MovementType.IN,
                "reference_type": stock_movement_service.ReferenceType.PURCHASE,
                "reference_id": expense.id,
            },
            commit=False,
        )
        await session.commit()
    await _post_expense_entry(session, tenant_id, expense)
    return expense


async def update_expense(
    session: AsyncSession, tenant_id: UUID, expense_id: UUID, payload: Any
) -> Expense | None:
    expense = await get_expense(session, tenant_id, expense_id)
    if not expense:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(expense, field, value)
    await session.commit()
    await session.refresh(expense)
    return expense


async def delete_expense(session: AsyncSession, tenant_id: UUID, expense_id: UUID) -> bool:
    result = await session.execute(
        delete(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_expenses",
    "get_expense",
    "create_expense",
    "update_expense",
    "delete_expense",
]
