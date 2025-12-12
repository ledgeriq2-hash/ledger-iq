from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics import PAYMENTS_CREATED
from app.models.payment import Payment
from app.services import journal_service, usage_service
from app.services.accounting_mapping import get_account_mapping


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def _load_payment_account_mapping(session: AsyncSession, tenant_id: UUID) -> dict[str, UUID | None]:
    mapping = await get_account_mapping(session, tenant_id)
    return {
        "cash": mapping.get("cash_account_id"),
        "accounts_receivable": mapping.get("accounts_receivable_account_id"),
    }


async def _post_payment_entry(session: AsyncSession, tenant_id: UUID, payment: Payment) -> None:
    mapping = await _load_payment_account_mapping(session, tenant_id)
    cash_account = mapping.get("cash")
    ar_account = mapping.get("accounts_receivable")
    if not cash_account or not ar_account:
        return

    amount = Decimal(str(payment.amount or 0))
    if amount <= 0:
        return

    payment_date = (
        payment.paid_at.date()
        if payment.paid_at
        else (payment.created_at.date() if hasattr(payment, "created_at") and payment.created_at else None)
    )
    lines = [
        {
            "account_id": cash_account,
            "debit": amount,
            "credit": Decimal("0"),
            "line_description": f"Payment {payment.id} receipt",
        },
        {
            "account_id": ar_account,
            "debit": Decimal("0"),
            "credit": amount,
            "line_description": f"Payment {payment.id} applied to receivable",
        },
    ]
    await journal_service.create_journal_entry_with_lines(
        session=session,
        tenant_id=tenant_id,
        date=payment_date or payment.created_at.date(),
        description=f"Payment {payment.id} receipt",
        reference=str(payment.id),
        lines=lines,
    )


async def list_payments(
    session: AsyncSession, tenant_id: UUID, page: int = 1, page_size: int = 50
) -> tuple[Sequence[Payment], int]:
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 50
    base_query = select(Payment).where(Payment.tenant_id == tenant_id).order_by(Payment.created_at.desc())
    total_result = await session.execute(
        select(func.count()).select_from(select(Payment.id).where(Payment.tenant_id == tenant_id).subquery())
    )
    total = int(total_result.scalar_one())
    result = await session.execute(base_query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def get_payment(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id, Payment.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_payments_for_customer(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID, limit: int = 20
) -> Sequence[Payment]:
    query = (
        select(Payment)
        .where(Payment.tenant_id == tenant_id, Payment.customer_id == customer_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def create_payment(session: AsyncSession, tenant_id: UUID, payload: Any) -> Payment:
    data = _to_dict(payload)
    payment = Payment(**data, tenant_id=tenant_id)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    try:
        PAYMENTS_CREATED.labels(tenant_id=str(tenant_id)).inc()
    except Exception:
        pass
    await _post_payment_entry(session, tenant_id, payment)
    await usage_service.record_payment_created(session, tenant_id)
    return payment


async def update_payment(
    session: AsyncSession, tenant_id: UUID, payment_id: UUID, payload: Any
) -> Payment | None:
    payment = await get_payment(session, tenant_id, payment_id)
    if not payment:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(payment, field, value)
    await session.commit()
    await session.refresh(payment)
    return payment


async def delete_payment(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> bool:
    result = await session.execute(
        delete(Payment).where(Payment.id == payment_id, Payment.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_payments",
    "list_payments_for_customer",
    "get_payment",
    "create_payment",
    "update_payment",
    "delete_payment",
]
