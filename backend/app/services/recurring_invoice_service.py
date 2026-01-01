from __future__ import annotations

import json
from calendar import monthrange
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring_invoice import RecurringInvoice
from app.schemas.invoice import InvoiceCreate, InvoicePublic
from app.schemas.recurring_invoice import (
    ALLOWED_FREQUENCIES,
    RecurringInvoiceCreate,
    RecurringInvoicePublic,
    RecurringInvoiceUpdate,
)
from app.services import invoice_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _ensure_tz(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _validate_frequency(value: str) -> str:
    value = (value or "").lower()
    if value not in ALLOWED_FREQUENCIES:
        raise ValueError(f"Unsupported frequency '{value}'")
    return value


def _next_run_from(base: datetime, frequency: str, interval: int = 1, day_of_month: int | None = None) -> datetime:
    base = _ensure_tz(base) or datetime.now(UTC)
    interval = max(1, interval or 1)
    freq = _validate_frequency(frequency)
    if freq == "daily":
        return base + timedelta(days=interval)
    if freq == "weekly":
        return base + timedelta(days=7 * interval)
    if freq == "monthly":
        # Advance by interval months, clamp day to month length.
        month = base.month - 1 + interval
        year = base.year + month // 12
        month = month % 12 + 1
        day = day_of_month or base.day
        last_day = monthrange(year, month)[1]
        day = min(day, last_day)
        return base.replace(year=year, month=month, day=day)
    # custom -> interpret as every N days
    return base + timedelta(days=interval)


def _serialize_template(template: InvoiceCreate | dict[str, Any]) -> str:
    if isinstance(template, InvoiceCreate):
        return template.model_dump_json()
    return json.dumps(template, default=str, ensure_ascii=False)


def _coerce_invoice_payload(template_json: str) -> InvoiceCreate:
    data = json.loads(template_json)
    return InvoiceCreate.model_validate(data)


def to_public_model(recurring: RecurringInvoice) -> RecurringInvoicePublic:
    template = _coerce_invoice_payload(recurring.template_json)
    customer = getattr(recurring, "customer", None)
    return RecurringInvoicePublic(
        id=recurring.id,
        customer_id=recurring.customer_id,
        frequency=recurring.frequency,
        interval=recurring.interval,
        day_of_month=recurring.day_of_month,
        next_run_at=recurring.next_run_at,
        last_run_at=recurring.last_run_at,
        template=template,
        customer=customer,
        created_at=recurring.created_at,
        updated_at=recurring.updated_at,
    )


async def list_recurring_invoices(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    frequency: str | None = None,
) -> tuple[Sequence[RecurringInvoice], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))

    query = select(RecurringInvoice).where(RecurringInvoice.tenant_id == tenant_id)
    if frequency:
        query = query.where(RecurringInvoice.frequency == frequency.lower())

    total_result = await session.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.order_by(RecurringInvoice.next_run_at.asc().nullsfirst(), RecurringInvoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_recurring_invoice(session: AsyncSession, tenant_id: UUID, recurring_id: UUID) -> RecurringInvoice | None:
    result = await session.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == recurring_id,
            RecurringInvoice.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def create_recurring_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: RecurringInvoiceCreate | dict[str, Any],
) -> RecurringInvoice:
    data = _to_dict(payload)
    frequency = _validate_frequency(data["frequency"])
    interval = max(1, int(data.get("interval") or 1))
    day_of_month = data.get("day_of_month")
    next_run_at = _ensure_tz(data.get("next_run_at"))
    template = data.get("template") or {}
    template_model = InvoiceCreate.model_validate(template)

    # Align customer IDs
    customer_id = data.get("customer_id") or template_model.customer_id
    if customer_id:
        customer_id = UUID(str(customer_id))
    template_model.customer_id = customer_id

    if not next_run_at:
        next_run_at = _next_run_from(datetime.now(UTC), frequency, interval, day_of_month)

    recurring = RecurringInvoice(
        customer_id=customer_id,
        frequency=frequency,
        interval=interval,
        day_of_month=day_of_month,
        next_run_at=next_run_at,
        template_json=_serialize_template(template_model),
        tenant_id=tenant_id,
    )
    session.add(recurring)
    await session.commit()
    await session.refresh(recurring)
    return recurring


async def update_recurring_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    recurring_id: UUID,
    payload: RecurringInvoiceUpdate | dict[str, Any],
) -> RecurringInvoice | None:
    recurring = await get_recurring_invoice(session, tenant_id, recurring_id)
    if not recurring:
        return None

    data = _to_dict(payload, exclude_unset=True)
    if "frequency" in data:
        recurring.frequency = _validate_frequency(data["frequency"])
    if "interval" in data and data["interval"] is not None:
        recurring.interval = max(1, int(data["interval"]))
    if "day_of_month" in data:
        recurring.day_of_month = data["day_of_month"]
    if "next_run_at" in data:
        recurring.next_run_at = _ensure_tz(data["next_run_at"])
    if "customer_id" in data and data["customer_id"]:
        recurring.customer_id = data["customer_id"]
    if "template" in data and data["template"] is not None:
        template_model = InvoiceCreate.model_validate(data["template"])
        if data.get("customer_id"):
            template_model.customer_id = data["customer_id"]
        else:
            template_model.customer_id = recurring.customer_id
        recurring.template_json = _serialize_template(template_model)

    await session.commit()
    await session.refresh(recurring)
    return recurring


async def delete_recurring_invoice(session: AsyncSession, tenant_id: UUID, recurring_id: UUID) -> bool:
    recurring = await get_recurring_invoice(session, tenant_id, recurring_id)
    if not recurring:
        return False
    await session.delete(recurring)
    await session.commit()
    return True


def _hydrate_invoice_payload(recurring: RecurringInvoice) -> InvoiceCreate:
    template = _coerce_invoice_payload(recurring.template_json)
    today = date.today()
    issue_date = today
    due_date = None
    if template.due_date:
        delta = template.due_date - template.issue_date
        due_date = today + delta
    template.issue_date = issue_date
    template.due_date = due_date
    template.customer_id = recurring.customer_id
    return template


async def run_recurring_invoice(session: AsyncSession, tenant_id: UUID, recurring_id: UUID) -> InvoicePublic | None:
    recurring = await get_recurring_invoice(session, tenant_id, recurring_id)
    if not recurring:
        return None

    invoice_payload = _hydrate_invoice_payload(recurring)
    invoice = await invoice_service.create_invoice(session, tenant_id, invoice_payload)
    await session.refresh(recurring)
    now = datetime.now(UTC)
    recurring.last_run_at = now
    recurring.next_run_at = _next_run_from(now, recurring.frequency, recurring.interval, recurring.day_of_month)
    await session.commit()
    await session.refresh(recurring)
    return InvoicePublic.model_validate(invoice)


async def process_due_recurring_invoices(session: AsyncSession, tenant_id: UUID | None = None, limit: int = 50) -> list[UUID]:
    now = datetime.now(UTC)
    query = select(RecurringInvoice).where(
        RecurringInvoice.next_run_at <= now,
    )
    if tenant_id:
        query = query.where(RecurringInvoice.tenant_id == tenant_id)
    result = await session.execute(query.order_by(RecurringInvoice.next_run_at.asc()).limit(limit))
    due_items = result.scalars().all()

    generated: list[UUID] = []
    for recurring in due_items:
        await session.refresh(recurring)
        invoice_payload = _hydrate_invoice_payload(recurring)
        invoice = await invoice_service.create_invoice(session, recurring.tenant_id, invoice_payload)
        generated.append(invoice.id)
        await session.refresh(recurring)
        now_ts = datetime.now(UTC)
        recurring.last_run_at = now_ts
        recurring.next_run_at = _next_run_from(now_ts, recurring.frequency, recurring.interval, recurring.day_of_month)
    if due_items:
        await session.commit()
    return generated


__all__ = [
    "list_recurring_invoices",
    "get_recurring_invoice",
    "create_recurring_invoice",
    "update_recurring_invoice",
    "delete_recurring_invoice",
    "run_recurring_invoice",
    "process_due_recurring_invoices",
    "to_public_model",
]
