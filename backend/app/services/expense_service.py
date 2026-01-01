from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.metrics import EXPENSES_CREATED
from app.models.expense import Expense
from app.services import stock_movement_service, treasury_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


@asynccontextmanager
async def _transaction_scope(session: AsyncSession):
    if session.in_transaction():
        await session.rollback()
    async with session.begin():
        yield


async def _post_expense_entry(
    session: AsyncSession,
    tenant_id: UUID,
    expense: Expense,
    actor_id: UUID | None,
    *,
    commit: bool = False,
) -> None:
    amount = Decimal(str(expense.amount or 0)).quantize(Decimal("0.01"))
    if amount <= 0:
        return

    await treasury_service.create_expense(
        session,
        tenant_id,
        amount=amount,
        supplier_id=expense.supplier_id,
        reference_type="expense",
        reference_id=expense.id,
        description=expense.description or f"Expense {expense.id}",
        entry_date=expense.expense_date,
        actor_id=actor_id,
        treasury_id=None,
        commit=commit,
    )


async def list_expenses(
    session: AsyncSession, tenant_id: UUID, page: int = 1, page_size: int = 50
) -> tuple[Sequence[Expense], int]:
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 50
    base_query = select(Expense).where(Expense.tenant_id == tenant_id).order_by(Expense.created_at.desc())
    total_result = await session.execute(
        select(func.count()).select_from(select(Expense.id).where(Expense.tenant_id == tenant_id).subquery())
    )
    total = int(total_result.scalar_one() or 0)
    result = await session.execute(base_query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def get_expense(session: AsyncSession, tenant_id: UUID, expense_id: UUID) -> Expense | None:
    result = await session.execute(
        select(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_expense(
    session: AsyncSession, tenant_id: UUID, payload: Any, *, actor_id: UUID | None = None
) -> Expense:
    data = _to_dict(payload)
    product_id = data.pop("product_id", None)
    quantity = data.pop("quantity", None)
    expense = Expense(**data, tenant_id=tenant_id)
    async with _transaction_scope(session):
        session.add(expense)
        await session.flush()
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
        # ledger entry keyed to the same transaction to ensure atomicity
        await _post_expense_entry(session, tenant_id, expense, actor_id, commit=False)
    await session.refresh(expense)
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
    _ = session, tenant_id, expense_id
    raise AppException(code="deletes_disabled", message="Deleting expenses is disabled", http_status=405)


__all__ = [
    "list_expenses",
    "get_expense",
    "create_expense",
    "update_expense",
    "delete_expense",
]
