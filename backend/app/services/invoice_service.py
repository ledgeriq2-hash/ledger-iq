from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.metrics import INVOICES_CREATED
from app.services import journal_service, usage_service, stock_movement_service
from app.services.accounting_mapping import get_account_mapping


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _ensure_line_total(data: dict[str, Any]) -> Decimal:
    quantity = Decimal(str(data.get("quantity") or 0))
    unit_price = Decimal(str(data.get("unit_price") or 0))
    tax_rate = Decimal(str(data.get("tax_rate") or 0))
    line_total = data.get("line_total")
    if line_total is not None:
        return Decimal(str(line_total))
    tax_multiplier = Decimal("1") + (tax_rate / Decimal("100"))
    return (quantity * unit_price * tax_multiplier).quantize(Decimal("0.01"))


def calculate_invoice_total(invoice: Invoice | Iterable[InvoiceItem]) -> Decimal:
    """
    Calculate the total amount for an invoice given its items.

    Accepts an Invoice (using its items relationship) or an iterable of InvoiceItem.
    """
    items: Iterable[InvoiceItem] = invoice.items if isinstance(invoice, Invoice) else invoice
    total = Decimal("0")
    for item in items:
        total += Decimal(str(item.line_total or 0))
    return total.quantize(Decimal("0.01"))


async def _load_invoice_account_mapping(session: AsyncSession, tenant_id: UUID) -> dict[str, UUID | None]:
    mapping = await get_account_mapping(session, tenant_id)
    return {
        "accounts_receivable": mapping.get("accounts_receivable_account_id"),
        "revenue": mapping.get("revenue_account_id"),
    }


async def _post_invoice_revenue(session: AsyncSession, tenant_id: UUID, invoice: Invoice) -> None:
    account_mapping = await _load_invoice_account_mapping(session, tenant_id)
    ar_account_id = account_mapping.get("accounts_receivable")
    revenue_account_id = account_mapping.get("revenue")
    if not ar_account_id or not revenue_account_id:
        return

    amount = Decimal(str(invoice.total_amount or 0))
    if amount <= 0:
        return
    lines = [
        {
            "account_id": ar_account_id,
            "debit": amount,
            "credit": Decimal("0"),
            "line_description": f"Invoice {invoice.id} - A/R",
        },
        {
            "account_id": revenue_account_id,
            "debit": Decimal("0"),
            "credit": amount,
            "line_description": f"Invoice {invoice.id} - Revenue",
        },
    ]
    await journal_service.create_journal_entry_with_lines(
        session=session,
        tenant_id=tenant_id,
        date=invoice.issue_date,
        description=f"Invoice {invoice.id} revenue recognition",
        reference=str(invoice.id),
        lines=lines,
    )


async def list_invoices(
    session: AsyncSession, tenant_id: UUID, page: int = 1, page_size: int = 50
) -> tuple[Sequence[Invoice], int]:
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 50
    base_query = select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.issue_date.desc())
    total_result = await session.execute(
        select(func.count()).select_from(select(Invoice.id).where(Invoice.tenant_id == tenant_id).subquery())
    )
    total = int(total_result.scalar_one())
    result = await session.execute(base_query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def get_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> Invoice | None:
    result = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _replace_invoice_items(
    session: AsyncSession, invoice: Invoice, items_data: list[dict[str, Any]] | None
) -> list[InvoiceItem]:
    await session.execute(
        delete(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id, InvoiceItem.tenant_id == invoice.tenant_id)
    )
    created_items: list[InvoiceItem] = []
    if not items_data:
        return created_items
    for item_data in items_data:
        line_data = dict(item_data)
        line_data["line_total"] = _ensure_line_total(line_data)
        item = InvoiceItem(**line_data, tenant_id=invoice.tenant_id, invoice_id=invoice.id)
        session.add(item)
        created_items.append(item)
    return created_items


async def create_invoice(session: AsyncSession, tenant_id: UUID, payload: Any) -> Invoice:
    data = _to_dict(payload)
    items_data = data.pop("items", None)
    invoice = Invoice(**data, tenant_id=tenant_id)
    session.add(invoice)
    await session.flush()
    created_items = await _replace_invoice_items(session, invoice, items_data)
    invoice.total_amount = calculate_invoice_total(created_items)
    await session.commit()
    await session.refresh(invoice)
    if invoice.status == InvoiceStatus.PAID:
        await _post_invoice_revenue(session, tenant_id, invoice)
    try:
        INVOICES_CREATED.labels(tenant_id=str(tenant_id)).inc()
    except Exception:
        pass
    await usage_service.record_invoice_created(session, tenant_id)
    await stock_movement_service.apply_invoice_movements(session, tenant_id, invoice)
    return invoice


async def update_invoice(
    session: AsyncSession, tenant_id: UUID, invoice_id: UUID, payload: Any
) -> Invoice | None:
    invoice = await get_invoice(session, tenant_id, invoice_id)
    if not invoice:
        return None
    was_paid = invoice.status == InvoiceStatus.PAID
    data = _to_dict(payload, exclude_unset=True)
    items_data = data.pop("items", None)
    for field, value in data.items():
        if field in {"id", "tenant_id", "items"}:
            continue
        setattr(invoice, field, value)
    if items_data is not None:
        created_items = await _replace_invoice_items(session, invoice, items_data)
        invoice.total_amount = calculate_invoice_total(created_items)
    await session.commit()
    await session.refresh(invoice)
    if not was_paid and invoice.status == InvoiceStatus.PAID:
        await _post_invoice_revenue(session, tenant_id, invoice)
    return invoice


async def delete_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> bool:
    await session.execute(
        delete(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id, InvoiceItem.tenant_id == tenant_id)
    )
    result = await session.execute(
        delete(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_invoices",
    "get_invoice",
    "create_invoice",
    "update_invoice",
    "delete_invoice",
    "calculate_invoice_total",
]
