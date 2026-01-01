from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.metrics import PAYMENTS_CREATED
from app.models.payment import Payment
from app.accounting.dto import RecordFinancialTransactionInput
from app.services import treasury_service, usage_service
from app.services.accounting_mapping import ACCOUNT_MAPPING_REQUIREMENTS, validate_tenant_account_mapping


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


async def _post_payment_entry(
    session: AsyncSession,
    tenant_id: UUID,
    payment: Payment,
    actor_id: UUID | None,
    *,
    commit: bool = False,
) -> None:
    amount = Decimal(str(payment.amount or 0)).quantize(Decimal("0.01"))
    if amount <= 0:
        return

    payment_date = getattr(payment, "event_date", None)
    if not payment_date:
        payment_date = (
            payment.paid_at.date()
            if payment.paid_at
            else (payment.created_at.date() if hasattr(payment, "created_at") and payment.created_at else None)
        )
    await treasury_service.create_receipt(
        session,
        tenant_id,
        amount=amount,
        customer_id=payment.customer_id,
        reference_type="payment",
        reference_id=payment.id,
        description=f"Payment {payment.id} receipt",
        entry_date=payment_date or payment.created_at.date(),
        actor_id=actor_id,
        treasury_id=None,
        commit=commit,
    )


async def _post_payment_adjustment_entry(
    session: AsyncSession,
    tenant_id: UUID,
    payment: Payment,
    amount: Decimal,
    reason: str | None,
    actor_id: UUID | None,
    *,
    commit: bool = False,
) -> None:
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["payment_adjustment"],
    )
    expense_account = mapping.get("expense")
    suspense_account = mapping.get("payables")

    delta = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
    if delta <= 0:
        return

    payment_date = getattr(payment, "event_date", None)
    if not payment_date:
        payment_date = (
            payment.paid_at.date()
            if payment.paid_at
            else (payment.created_at.date() if hasattr(payment, "created_at") and payment.created_at else None)
        )
    note = f": {reason}" if reason else ""
    description = f"Payment {payment.id} adjustment{note}"
    await record_financial_transaction(
        session,
        RecordFinancialTransactionInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            date=payment_date or payment.created_at.date(),
            description=description,
            reference_type="payment_adjustment",
            reference_id=payment.id,
            lines=[
                {
                    "account_id": expense_account,
                    "debit": delta,
                    "credit": Decimal("0"),
                    "entity_type": "client",
                    "entity_id": payment.customer_id,
                    "reference_type": "payment_adjustment",
                    "reference_id": payment.id,
                    "description": description,
                },
                {
                    "account_id": suspense_account,
                    "debit": Decimal("0"),
                    "credit": delta,
                    "entity_type": "client",
                    "entity_id": payment.customer_id,
                    "reference_type": "payment_adjustment",
                    "reference_id": payment.id,
                    "description": description,
                },
            ],
            treasury_movement=None,
        ),
        commit=commit,
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


async def create_payment(
    session: AsyncSession, tenant_id: UUID, payload: Any, *, actor_id: UUID | None = None
) -> Payment:
    data = _to_dict(payload)
    payment = Payment(**data, tenant_id=tenant_id)
    async with _transaction_scope(session):
        session.add(payment)
        await session.flush()
        try:
            PAYMENTS_CREATED.labels(tenant_id=str(tenant_id)).inc()
        except Exception:
            pass
        await _post_payment_entry(session, tenant_id, payment, actor_id, commit=False)
        await usage_service.record_payment_created(session, tenant_id, commit=False)
    await session.refresh(payment)
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


async def adjust_payment(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Payment | None:
    data = _to_dict(payload)
    delta = Decimal(str(data.get("amount") or 0)).quantize(Decimal("0.01"))
    reason = data.get("reason")
    if delta <= 0:
        raise AppException(code="adjustment_amount_invalid", message="Adjustment must be greater than zero", http_status=422)

    async with _transaction_scope(session):
        payment = await get_payment(session, tenant_id, payment_id)
        if not payment:
            return None
        await _post_payment_adjustment_entry(
            session,
            tenant_id,
            payment,
            delta,
            reason,
            actor_id,
            commit=False,
        )
    await session.refresh(payment)
    return payment


async def delete_payment(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> bool:
    _ = session, tenant_id, payment_id
    raise AppException(code="deletes_disabled", message="Deleting payments is disabled", http_status=405)


__all__ = [
    "list_payments",
    "list_payments_for_customer",
    "get_payment",
    "create_payment",
    "update_payment",
    "adjust_payment",
    "delete_payment",
]
