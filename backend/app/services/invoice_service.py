from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.dto import RecordFinancialTransactionInput
from app.accounting.use_cases.record_financial_transaction import record_financial_transaction
from app.core.exceptions import AppException
from app.metrics import INVOICES_CREATED
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.payment import Payment
from app.schemas.invoice import InvoiceCreate
from app.services import stock_movement_service, treasury_service, usage_service
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
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["invoice_posting"],
    )
    return {
        "accounts_receivable": mapping.get("accounts_receivable_account_id"),
        "revenue": mapping.get("revenue_account_id"),
    }


async def _sum_invoice_payments(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.tenant_id == tenant_id,
            Payment.invoice_id == invoice_id,
        )
    )
    return Decimal(str(result.scalar_one() or 0)).quantize(Decimal("0.01"))


def _derive_invoice_status(*, total_amount: Decimal, total_paid: Decimal, due_date: date | None) -> InvoiceStatus:
    total_amount = Decimal(str(total_amount or 0)).quantize(Decimal("0.01"))
    total_paid = Decimal(str(total_paid or 0)).quantize(Decimal("0.01"))

    if total_amount > 0 and total_paid >= total_amount:
        return InvoiceStatus.PAID
    if total_paid > 0:
        return InvoiceStatus.PARTIAL
    if due_date and due_date < date.today():
        return InvoiceStatus.OVERDUE
    return InvoiceStatus.POSTED


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
    invoice_model = InvoiceCreate.model_validate(data)
    items_data = [item.model_dump() for item in invoice_model.items or []]
    invoice_data = invoice_model.model_dump(exclude={"items"})
    if isinstance(invoice_data.get("issue_date"), str):
        invoice_data["issue_date"] = date.fromisoformat(invoice_data["issue_date"])
    if isinstance(invoice_data.get("due_date"), str):
        invoice_data["due_date"] = date.fromisoformat(invoice_data["due_date"])
    invoice_data["status"] = InvoiceStatus.DRAFT
    invoice = Invoice(**invoice_data, tenant_id=tenant_id)
    async with _transaction_scope(session):
        session.add(invoice)
        await session.flush()
        created_items = await _replace_invoice_items(session, invoice, items_data)
        invoice.total_amount = calculate_invoice_total(created_items)
        try:
            INVOICES_CREATED.labels(tenant_id=str(tenant_id)).inc()
        except Exception:
            pass
        await usage_service.record_invoice_created(session, tenant_id, commit=False)
    await session.refresh(invoice)
    return invoice


async def post_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Invoice:
    async with _transaction_scope(session):
        invoice = await get_invoice(session, tenant_id, invoice_id)
        if not invoice:
            raise AppException(code="invoice_not_found", message="Invoice not found", http_status=404)
        if invoice.status != InvoiceStatus.DRAFT:
            raise AppException(code="invoice_not_draft", message="Only draft invoices can be posted", http_status=409)

        amount = Decimal(str(invoice.total_amount or 0)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise AppException(code="invoice_total_invalid", message="Invoice total must be greater than zero", http_status=409)

        mapping = await _load_invoice_account_mapping(session, tenant_id)
        ar_account_id = mapping.get("accounts_receivable")
        revenue_account_id = mapping.get("revenue")

        await record_financial_transaction(
            session,
            RecordFinancialTransactionInput(
                tenant_id=tenant_id,
                actor_id=actor_id,
                date=invoice.issue_date,
                description=f"Invoice {invoice.id} posted",
                reference_type="invoice",
                reference_id=invoice.id,
                lines=[
                    {
                        "account_id": ar_account_id,
                        "debit": amount,
                        "credit": Decimal("0"),
                        "entity_type": "client",
                        "entity_id": invoice.customer_id,
                        "reference_type": "invoice",
                        "reference_id": invoice.id,
                        "description": f"Invoice {invoice.id} receivable",
                    },
                    {
                        "account_id": revenue_account_id,
                        "debit": Decimal("0"),
                        "credit": amount,
                        "entity_type": "client",
                        "entity_id": invoice.customer_id,
                        "reference_type": "invoice",
                        "reference_id": invoice.id,
                        "description": f"Invoice {invoice.id} revenue",
                    },
                ],
                treasury_movement=None,
            ),
            commit=False,
        )

        await stock_movement_service.apply_invoice_movements(session, tenant_id, invoice, commit=False)

        total_paid = await _sum_invoice_payments(session, tenant_id, invoice.id)
        invoice.status = _derive_invoice_status(total_amount=amount, total_paid=total_paid, due_date=invoice.due_date)

    await session.refresh(invoice)
    return invoice


async def record_partial_payment(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Invoice:
    async with _transaction_scope(session):
        invoice = await get_invoice(session, tenant_id, invoice_id)
        if not invoice:
            raise AppException(code="invoice_not_found", message="Invoice not found", http_status=404)
        if invoice.status == InvoiceStatus.DRAFT:
            raise AppException(code="invoice_not_posted", message="Invoice must be posted before payments", http_status=409)

        data = _to_dict(payload)
        amount = Decimal(str(data.get("amount") or 0)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise AppException(code="payment_amount_invalid", message="Payment amount must be greater than zero", http_status=422)

        payment = Payment(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            amount=amount,
            method=str(data.get("method") or ""),
            reference=data.get("reference"),
            paid_at=data.get("paid_at"),
        )
        if not payment.method:
            raise AppException(code="payment_method_required", message="Payment method is required", http_status=422)

        session.add(payment)
        await session.flush()

        payment_date = payment.paid_at.date() if payment.paid_at else payment.created_at.date()
        await treasury_service.create_receipt(
            session,
            tenant_id,
            amount=amount,
            customer_id=invoice.customer_id,
            reference_type="payment",
            reference_id=payment.id,
            description=f"Payment {payment.id} for invoice {invoice.id}",
            entry_date=payment_date,
            actor_id=actor_id,
            commit=False,
        )

        total_paid = await _sum_invoice_payments(session, tenant_id, invoice.id)
        invoice.status = _derive_invoice_status(
            total_amount=Decimal(str(invoice.total_amount or 0)),
            total_paid=total_paid,
            due_date=invoice.due_date,
        )

    await session.refresh(invoice)
    return invoice


async def update_invoice(
    session: AsyncSession, tenant_id: UUID, invoice_id: UUID, payload: Any
) -> Invoice | None:
    invoice = await get_invoice(session, tenant_id, invoice_id)
    if not invoice:
        return None
    if invoice.status != InvoiceStatus.DRAFT:
        raise AppException(code="invoice_not_editable", message="Only draft invoices can be edited", http_status=409)
    data = _to_dict(payload, exclude_unset=True)
    items_data = data.pop("items", None)
    if data.get("status") is not None and data.get("status") != InvoiceStatus.DRAFT:
        raise AppException(code="invoice_status_immutable", message="Invoice status is managed by workflow", http_status=409)
    for field, value in data.items():
        if field in {"id", "tenant_id", "items"}:
            continue
        setattr(invoice, field, value)
    if items_data is not None:
        created_items = await _replace_invoice_items(session, invoice, items_data)
        invoice.total_amount = calculate_invoice_total(created_items)
    await session.commit()
    await session.refresh(invoice)
    return invoice


async def delete_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> bool:
    async with _transaction_scope(session):
        invoice = await get_invoice(session, tenant_id, invoice_id)
        if not invoice:
            return False
        if invoice.status != InvoiceStatus.DRAFT:
            raise AppException(
                code="invoice_delete_not_allowed",
                message="Only draft invoices can be deleted",
                http_status=409,
            )

        await session.execute(delete(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id, InvoiceItem.tenant_id == tenant_id))
        await session.delete(invoice)
    return True


__all__ = [
    "list_invoices",
    "get_invoice",
    "create_invoice",
    "post_invoice",
    "record_partial_payment",
    "update_invoice",
    "delete_invoice",
    "calculate_invoice_total",
]
