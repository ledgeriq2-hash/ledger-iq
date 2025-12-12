from __future__ import annotations

from typing import Any, Sequence, Tuple
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.customer import Customer
from app.services import usage_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_customers(
    session: AsyncSession, tenant_id: UUID, page: int = 1, page_size: int = 50
) -> tuple[Sequence[Customer], int]:
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 50
    base_query = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.created_at.desc())
    total_result = await session.execute(
        select(func.count()).select_from(select(Customer.id).where(Customer.tenant_id == tenant_id).subquery())
    )
    total = int(total_result.scalar_one())
    result = await session.execute(base_query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def get_customer(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Customer | None:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_customer(session: AsyncSession, tenant_id: UUID, payload: Any) -> Customer:
    data = _to_dict(payload)
    customer = Customer(**data, tenant_id=tenant_id)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    await usage_service.record_customer_created(session, tenant_id)
    return customer


async def update_customer(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID, payload: Any
) -> Customer | None:
    customer = await get_customer(session, tenant_id, customer_id)
    if not customer:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(customer, field, value)
    await session.commit()
    await session.refresh(customer)
    return customer


async def delete_customer(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> bool:
    result = await session.execute(
        delete(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


async def get_customer_with_open_invoices(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> Tuple[Customer | None, Sequence[Invoice]]:
    customer = await get_customer(session, tenant_id, customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        return None, []
    invoices_result = await session.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.customer_id == customer_id,
            Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
        )
    )
    invoices = invoices_result.scalars().all()
    return customer, invoices


__all__ = [
    "list_customers",
    "get_customer",
    "create_customer",
    "update_customer",
    "delete_customer",
    "get_customer_with_open_invoices",
]
