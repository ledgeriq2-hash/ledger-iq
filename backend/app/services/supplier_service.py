from __future__ import annotations

from typing import Any, Sequence, Tuple
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.supplier import Supplier


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_suppliers(session: AsyncSession, tenant_id: UUID) -> Sequence[Supplier]:
    result = await session.execute(select(Supplier).where(Supplier.tenant_id == tenant_id))
    return result.scalars().all()


async def get_supplier(session: AsyncSession, tenant_id: UUID, supplier_id: UUID) -> Supplier | None:
    result = await session.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_supplier(session: AsyncSession, tenant_id: UUID, payload: Any) -> Supplier:
    data = _to_dict(payload)
    supplier = Supplier(**data, tenant_id=tenant_id)
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return supplier


async def update_supplier(
    session: AsyncSession, tenant_id: UUID, supplier_id: UUID, payload: Any
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id)
    if not supplier:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(supplier, field, value)
    await session.commit()
    await session.refresh(supplier)
    return supplier


async def delete_supplier(session: AsyncSession, tenant_id: UUID, supplier_id: UUID) -> bool:
    result = await session.execute(
        delete(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


async def get_supplier_with_expenses(
    session: AsyncSession, tenant_id: UUID, supplier_id: UUID
) -> Tuple[Supplier | None, Sequence[Expense]]:
    supplier = await get_supplier(session, tenant_id, supplier_id)
    if not supplier or getattr(supplier, "is_deleted", False):
        return None, []
    expenses_result = await session.execute(
        select(Expense).where(Expense.tenant_id == tenant_id, Expense.supplier_id == supplier_id)
    )
    expenses = expenses_result.scalars().all()
    return supplier, expenses


__all__ = [
    "list_suppliers",
    "get_supplier",
    "create_supplier",
    "update_supplier",
    "delete_supplier",
    "get_supplier_with_expenses",
]
