from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.core.exceptions import AppException
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.customer import Customer, CustomerStatus
from app.models.customer_receipt import CustomerReceipt, CustomerReceiptStatus
from app.models.customer_receipt_allocation import CustomerReceiptAllocation
from app.models.journal_entry import JournalEntry
from app.models.sales_invoice import SalesInvoice, SalesInvoiceStatus
from app.schemas.journals import JournalLineCreate
from app.services import settings_service
from app.services.ledger_service import DEFAULT_BASE_CURRENCY, LedgerService, STATUS_POSTED, STATUS_REVERSED
from app.services.period_guard import PeriodGuard


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _quantize(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _quantize_fx(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.000001"))


@asynccontextmanager
async def _transaction_scope(session: AsyncSession):
    if session.in_transaction():
        await session.rollback()
    async with session.begin():
        yield


async def _resolve_currency(session: AsyncSession, tenant_id: UUID, currency_code: str | None) -> str:
    candidate = (currency_code or "").strip().upper()
    if candidate:
        return candidate
    fallback = await settings_service.get_base_currency(session, tenant_id)
    return fallback or DEFAULT_BASE_CURRENCY


def _resolve_fx_rate(doc_currency: str, base_currency: str, fx_rate: Decimal | None) -> Decimal:
    if doc_currency == base_currency:
        return Decimal("1.000000")
    rate = _quantize_fx(fx_rate)
    if rate <= 0:
        raise AppException(
            code="fx_rate_required",
            message="FX rate is required for non-base currency receipts",
            http_status=422,
        )
    return rate


async def _get_account(session: AsyncSession, tenant_id: UUID, account_id: UUID) -> Account:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise AppException(code="ledger_account_not_found", message="Ledger account not found", http_status=404)
    if getattr(account, "is_active", True) is False:
        raise AppException(code="ledger_account_inactive", message="Ledger account is inactive", http_status=409)
    return account


async def _get_ar_control_account_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AR_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message="AR control account mapping is missing",
            details={"key": "AR_CONTROL"},
            http_status=422,
        )
    await _get_account(session, tenant_id, mapping.account_id)
    return mapping.account_id


async def _get_customer_credit_account_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "CUSTOMER_CREDIT",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message="Customer credit account mapping is missing",
            details={"key": "CUSTOMER_CREDIT"},
            http_status=422,
        )
    await _get_account(session, tenant_id, mapping.account_id)
    return mapping.account_id


async def _get_customer(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalar_one_or_none()
    if not customer or customer.status == CustomerStatus.DELETED:
        raise AppException(code="customer_not_found", message="Customer not found", http_status=404)
    return customer


def _normalize_receipt_no(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise AppException(code="customer_receipt_no_required", message="Receipt number is required", http_status=422)
    return cleaned


async def _next_receipt_no(session: AsyncSession, tenant_id: UUID) -> str:
    prefix = "RCPT-"
    pattern = f"^{prefix}\\d{{6}}$"
    result = await session.execute(
        select(func.max(CustomerReceipt.receipt_no)).where(
            CustomerReceipt.tenant_id == tenant_id,
            CustomerReceipt.receipt_no.is_not(None),
            CustomerReceipt.receipt_no.op("~")(pattern),
        )
    )
    max_no = result.scalar_one_or_none()
    next_value = 1
    if max_no:
        try:
            next_value = int(str(max_no).replace(prefix, "")) + 1
        except ValueError:
            next_value = 1
    return f"{prefix}{next_value:06d}"


async def _ensure_receipt_no(session: AsyncSession, tenant_id: UUID, current: str | None) -> str:
    cleaned = (current or "").strip()
    if cleaned:
        return cleaned
    for _ in range(5):
        candidate = await _next_receipt_no(session, tenant_id)
        exists = await session.execute(
            select(CustomerReceipt.id).where(
                CustomerReceipt.tenant_id == tenant_id,
                CustomerReceipt.receipt_no == candidate,
            )
        )
        if exists.scalar_one_or_none():
            continue
        return candidate
    raise AppException(
        code="customer_receipt_no_conflict",
        message="Unable to generate unique receipt number",
        http_status=409,
    )


async def _get_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    *,
    include_allocations: bool = True,
) -> CustomerReceipt | None:
    stmt = select(CustomerReceipt).where(
        CustomerReceipt.id == receipt_id, CustomerReceipt.tenant_id == tenant_id
    )
    if include_allocations:
        stmt = stmt.options(selectinload(CustomerReceipt.allocations))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> SalesInvoice | None:
    result = await session.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice_id, SalesInvoice.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _invoice_total(invoice: SalesInvoice) -> Decimal:
    total = getattr(invoice, "total", None)
    if total is None:
        total = invoice.total_amount
    return _quantize(total)


async def _sum_receipt_allocations(session: AsyncSession, tenant_id: UUID, receipt_id: UUID) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(CustomerReceiptAllocation.amount), 0)).where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.receipt_id == receipt_id,
        )
    )
    return _quantize(result.scalar_one() or 0)


async def _sum_posted_invoice_allocations(
    session: AsyncSession, tenant_id: UUID, invoice_id: UUID
) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(CustomerReceiptAllocation.amount), 0))
        .join(CustomerReceipt, CustomerReceiptAllocation.receipt_id == CustomerReceipt.id)
        .where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.sales_invoice_id == invoice_id,
            CustomerReceipt.status == CustomerReceiptStatus.POSTED,
        )
    )
    return _quantize(result.scalar_one() or 0)


async def _find_receipt_entry(
    session: AsyncSession, tenant_id: UUID, receipt_id: UUID
) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "customer_receipt",
            JournalEntry.source_id == receipt_id,
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return result.scalars().first()


async def _find_reversal_entry(session: AsyncSession, tenant_id: UUID, entry_id: UUID) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            (JournalEntry.reversed_of_id == entry_id) | (JournalEntry.reversal_of_entry_id == entry_id),
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return result.scalars().first()


async def list_receipts(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    *,
    customer_id: UUID | None = None,
    status: CustomerReceiptStatus | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[Sequence[CustomerReceipt], int]:
    page = max(1, page)
    page_size = max(1, page_size)

    query = select(CustomerReceipt).where(CustomerReceipt.tenant_id == tenant_id)
    if customer_id:
        query = query.where(CustomerReceipt.customer_id == customer_id)
    if status:
        try:
            normalized = status if isinstance(status, CustomerReceiptStatus) else CustomerReceiptStatus(str(status))
        except Exception as exc:
            raise AppException(
                code="customer_receipt_status_invalid",
                message="Invalid customer receipt status",
                http_status=422,
            ) from exc
        query = query.where(CustomerReceipt.status == normalized)
    if date_from:
        query = query.where(CustomerReceipt.receipt_date >= date_from)
    if date_to:
        query = query.where(CustomerReceipt.receipt_date <= date_to)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.options(selectinload(CustomerReceipt.allocations))
        .order_by(CustomerReceipt.receipt_date.desc(), CustomerReceipt.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_receipt(session: AsyncSession, tenant_id: UUID, receipt_id: UUID) -> CustomerReceipt | None:
    return await _get_receipt(session, tenant_id, receipt_id, include_allocations=True)


async def create_receipt(session: AsyncSession, tenant_id: UUID, payload: Any) -> CustomerReceipt:
    data = _to_dict(payload)
    raw_receipt_no = data.get("receipt_no")
    receipt_no = _normalize_receipt_no(raw_receipt_no) if raw_receipt_no else None
    customer_id = data.get("customer_id")
    if not customer_id:
        raise AppException(code="customer_id_required", message="Customer is required", http_status=422)
    await _get_customer(session, tenant_id, customer_id)
    receipt_date = data.get("receipt_date")
    if not receipt_date:
        raise AppException(code="receipt_date_required", message="Receipt date is required", http_status=422)
    amount_total = _quantize(data.get("amount_total"))
    if amount_total <= 0:
        raise AppException(
            code="customer_receipt_total_invalid",
            message="Receipt total must be greater than zero",
            http_status=422,
        )
    cash_account_id = data.get("cash_account_id")
    if not cash_account_id:
        raise AppException(
            code="customer_receipt_cash_required",
            message="Cash account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, cash_account_id)

    if receipt_no:
        existing = await session.execute(
            select(CustomerReceipt.id).where(
                CustomerReceipt.tenant_id == tenant_id,
                CustomerReceipt.receipt_no == receipt_no,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="customer_receipt_no_exists",
                message="Receipt number already exists",
                http_status=409,
            )

    receipt = CustomerReceipt(
        tenant_id=tenant_id,
        customer_id=customer_id,
        receipt_no=receipt_no,
        receipt_date=receipt_date,
        currency_code=data.get("currency_code"),
        fx_rate=_quantize_fx(data.get("fx_rate")) if data.get("fx_rate") is not None else None,
        amount_total=amount_total,
        memo=data.get("memo"),
        cash_account_id=cash_account_id,
        status=CustomerReceiptStatus.DRAFT,
    )

    async with _transaction_scope(session):
        session.add(receipt)
        await session.flush()
    await session.refresh(receipt)
    return receipt


async def update_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    payload: Any,
) -> CustomerReceipt | None:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        return None
    if receipt.status != CustomerReceiptStatus.DRAFT:
        raise AppException(
            code="customer_receipt_not_editable",
            message="Only draft receipts can be edited",
            http_status=409,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "receipt_no" in data:
        if data["receipt_no"] is None:
            receipt.receipt_no = None
        else:
            receipt_no = _normalize_receipt_no(data["receipt_no"])
            existing = await session.execute(
                select(CustomerReceipt.id).where(
                    CustomerReceipt.tenant_id == tenant_id,
                    CustomerReceipt.receipt_no == receipt_no,
                    CustomerReceipt.id != receipt_id,
                )
            )
            if existing.scalar_one_or_none():
                raise AppException(
                    code="customer_receipt_no_exists",
                    message="Receipt number already exists",
                    http_status=409,
                )
            receipt.receipt_no = receipt_no
    if "receipt_date" in data and data["receipt_date"] is not None:
        receipt.receipt_date = data["receipt_date"]
    if "currency_code" in data:
        receipt.currency_code = data.get("currency_code")
        allocations_result = await session.execute(
            select(CustomerReceiptAllocation.sales_invoice_id).where(
                CustomerReceiptAllocation.tenant_id == tenant_id,
                CustomerReceiptAllocation.receipt_id == receipt_id,
            )
        )
        invoice_ids = [row[0] for row in allocations_result.all()]
        if invoice_ids:
            receipt_currency = await _resolve_currency(session, tenant_id, receipt.currency_code)
            invoices_result = await session.execute(
                select(SalesInvoice.id, SalesInvoice.currency_code).where(
                    SalesInvoice.tenant_id == tenant_id,
                    SalesInvoice.id.in_(invoice_ids),
                )
            )
            invoice_currency_map = {row[0]: row[1] for row in invoices_result.all()}
            for invoice_id in invoice_ids:
                invoice_currency = await _resolve_currency(
                    session, tenant_id, invoice_currency_map.get(invoice_id)
                )
                if invoice_currency != receipt_currency:
                    raise AppException(
                        code="customer_receipt_currency_mismatch",
                        message="Receipt currency must match all allocated invoices",
                        http_status=409,
                    )
    if "fx_rate" in data:
        receipt.fx_rate = _quantize_fx(data.get("fx_rate")) if data.get("fx_rate") is not None else None
    if "memo" in data:
        receipt.memo = data.get("memo")
    if "customer_id" in data and data["customer_id"] is not None:
        await _get_customer(session, tenant_id, data["customer_id"])
        receipt.customer_id = data["customer_id"]
    if "cash_account_id" in data and data["cash_account_id"] is not None:
        await _get_account(session, tenant_id, data["cash_account_id"])
        receipt.cash_account_id = data["cash_account_id"]
    if "amount_total" in data and data["amount_total"] is not None:
        amount_total = _quantize(data["amount_total"])
        if amount_total <= 0:
            raise AppException(
                code="customer_receipt_total_invalid",
                message="Receipt total must be greater than zero",
                http_status=422,
            )
        allocated = await _sum_receipt_allocations(session, tenant_id, receipt_id)
        if allocated > amount_total:
            raise AppException(
                code="customer_receipt_allocation_exceeds_total",
                message="Allocations exceed receipt total",
                http_status=409,
            )
        receipt.amount_total = amount_total

    await session.commit()
    await session.refresh(receipt)
    return receipt


async def list_receipt_allocations(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
) -> list[CustomerReceiptAllocation]:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)
    result = await session.execute(
        select(CustomerReceiptAllocation)
        .where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.receipt_id == receipt_id,
        )
        .order_by(CustomerReceiptAllocation.created_at.asc())
    )
    return list(result.scalars().all())


async def _validate_allocation_target(
    session: AsyncSession,
    tenant_id: UUID,
    receipt: CustomerReceipt,
    sales_invoice_id: UUID,
    amount: Decimal,
) -> None:
    invoice = await _get_invoice(session, tenant_id, sales_invoice_id)
    if not invoice:
        raise AppException(
            code="sales_invoice_not_found",
            message="Sales invoice not found",
            http_status=404,
        )
    if invoice.status == SalesInvoiceStatus.REVERSED:
        raise AppException(
            code="sales_invoice_reversed",
            message="Cannot allocate to reversed sales invoice",
            http_status=409,
        )
    if invoice.status != SalesInvoiceStatus.POSTED:
        raise AppException(
            code="sales_invoice_not_posted",
            message="Sales invoice must be posted before allocation",
            http_status=409,
        )
    if invoice.customer_id != receipt.customer_id:
        raise AppException(
            code="customer_receipt_allocation_invalid",
            message="Allocation must reference an invoice for the same customer",
            http_status=409,
        )
    receipt_currency = await _resolve_currency(session, tenant_id, receipt.currency_code)
    invoice_currency = await _resolve_currency(session, tenant_id, invoice.currency_code)
    if receipt_currency != invoice_currency:
        raise AppException(
            code="customer_receipt_currency_mismatch",
            message="Receipt currency must match invoice currency",
            http_status=409,
        )
    invoice_total = _invoice_total(invoice)
    allocated = await _sum_posted_invoice_allocations(session, tenant_id, sales_invoice_id)
    if allocated + amount > invoice_total:
        raise AppException(
            code="customer_receipt_allocation_exceeds_invoice",
            message="Allocation exceeds invoice remaining balance",
            http_status=409,
        )


async def add_receipt_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    payload: Any,
) -> CustomerReceiptAllocation:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)
    if receipt.status != CustomerReceiptStatus.DRAFT:
        raise AppException(
            code="customer_receipt_not_editable",
            message="Only draft receipts can be edited",
            http_status=409,
        )

    data = _to_dict(payload)
    sales_invoice_id = data.get("sales_invoice_id")
    if not sales_invoice_id:
        raise AppException(
            code="customer_receipt_allocation_invalid",
            message="Sales invoice is required",
            http_status=422,
        )
    amount = _quantize(data.get("amount"))
    if amount <= 0:
        raise AppException(
            code="customer_receipt_allocation_invalid",
            message="Allocation amount must be greater than zero",
            http_status=422,
        )

    existing = await session.execute(
        select(CustomerReceiptAllocation.id).where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.receipt_id == receipt_id,
            CustomerReceiptAllocation.sales_invoice_id == sales_invoice_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="customer_receipt_allocation_exists",
            message="Allocation already exists for this invoice",
            http_status=409,
        )

    allocated = await _sum_receipt_allocations(session, tenant_id, receipt_id)
    if allocated + amount > _quantize(receipt.amount_total):
        raise AppException(
            code="customer_receipt_allocation_exceeds_total",
            message="Allocations exceed receipt total",
            http_status=409,
        )

    await _validate_allocation_target(session, tenant_id, receipt, sales_invoice_id, amount)

    allocation = CustomerReceiptAllocation(
        tenant_id=tenant_id,
        receipt_id=receipt_id,
        sales_invoice_id=sales_invoice_id,
        amount=amount,
    )
    session.add(allocation)
    await session.commit()
    await session.refresh(allocation)
    return allocation


async def update_receipt_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    allocation_id: UUID,
    payload: Any,
) -> CustomerReceiptAllocation:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)
    if receipt.status != CustomerReceiptStatus.DRAFT:
        raise AppException(
            code="customer_receipt_not_editable",
            message="Only draft receipts can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(CustomerReceiptAllocation).where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.receipt_id == receipt_id,
            CustomerReceiptAllocation.id == allocation_id,
        )
    )
    allocation = result.scalar_one_or_none()
    if not allocation:
        raise AppException(
            code="customer_receipt_allocation_not_found",
            message="Receipt allocation not found",
            http_status=404,
        )

    data = _to_dict(payload, exclude_unset=True)
    sales_invoice_id = data.get("sales_invoice_id", allocation.sales_invoice_id)
    amount = _quantize(data.get("amount", allocation.amount))
    if amount <= 0:
        raise AppException(
            code="customer_receipt_allocation_invalid",
            message="Allocation amount must be greater than zero",
            http_status=422,
        )

    if sales_invoice_id != allocation.sales_invoice_id:
        existing = await session.execute(
            select(CustomerReceiptAllocation.id).where(
                CustomerReceiptAllocation.tenant_id == tenant_id,
                CustomerReceiptAllocation.receipt_id == receipt_id,
                CustomerReceiptAllocation.sales_invoice_id == sales_invoice_id,
                CustomerReceiptAllocation.id != allocation_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="customer_receipt_allocation_exists",
                message="Allocation already exists for this invoice",
                http_status=409,
            )

    allocated = await _sum_receipt_allocations(session, tenant_id, receipt_id)
    allocated = allocated - _quantize(allocation.amount) + amount
    if allocated > _quantize(receipt.amount_total):
        raise AppException(
            code="customer_receipt_allocation_exceeds_total",
            message="Allocations exceed receipt total",
            http_status=409,
        )

    await _validate_allocation_target(session, tenant_id, receipt, sales_invoice_id, amount)

    allocation.sales_invoice_id = sales_invoice_id
    allocation.amount = amount

    await session.commit()
    await session.refresh(allocation)
    return allocation


async def delete_receipt_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    allocation_id: UUID,
) -> bool:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)
    if receipt.status != CustomerReceiptStatus.DRAFT:
        raise AppException(
            code="customer_receipt_not_editable",
            message="Only draft receipts can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(CustomerReceiptAllocation).where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.receipt_id == receipt_id,
            CustomerReceiptAllocation.id == allocation_id,
        )
    )
    allocation = result.scalar_one_or_none()
    if not allocation:
        return False
    await session.delete(allocation)
    await session.commit()
    return True


async def post_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> CustomerReceipt:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=True)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)

    if receipt.status == CustomerReceiptStatus.POSTED:
        raise AppException(
            code="customer_receipt_already_posted",
            message="Receipt has already been posted",
            http_status=409,
        )
    if receipt.status == CustomerReceiptStatus.REVERSED:
        raise AppException(
            code="customer_receipt_not_draft",
            message="Only draft receipts can be posted",
            http_status=409,
        )
    if receipt.posting_journal_entry_id:
        raise AppException(
            code="customer_receipt_already_posted",
            message="Receipt has already been posted",
            http_status=409,
        )

    amount_total = _quantize(receipt.amount_total)
    if amount_total <= 0:
        raise AppException(
            code="customer_receipt_total_invalid",
            message="Receipt total must be greater than zero",
            http_status=422,
        )
    if not receipt.cash_account_id:
        raise AppException(
            code="customer_receipt_cash_required",
            message="Cash account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, receipt.cash_account_id)

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=receipt.receipt_date)

    customer = await _get_customer(session, tenant_id, receipt.customer_id)
    if customer.status == CustomerStatus.INACTIVE:
        raise AppException(
            code="customer_inactive",
            message="Customer is inactive",
            http_status=409,
        )

    existing_entry = await _find_receipt_entry(session, tenant_id, receipt_id)
    if existing_entry and existing_entry.status == STATUS_POSTED:
        receipt.status = CustomerReceiptStatus.POSTED
        receipt.posted_at = existing_entry.posted_at or existing_entry.posting_date or datetime.now(UTC)
        receipt.posting_journal_entry_id = existing_entry.id
        await session.commit()
        await session.refresh(receipt)
        raise AppException(
            code="customer_receipt_already_posted",
            message="Receipt has already been posted",
            http_status=409,
        )

    applied_total = Decimal("0.00")
    for allocation in receipt.allocations:
        applied_total += _quantize(allocation.amount)
    applied_total = _quantize(applied_total)
    if applied_total > amount_total:
        raise AppException(
            code="customer_receipt_allocation_exceeds_total",
            message="Allocations exceed receipt total",
            http_status=409,
        )

    for allocation in receipt.allocations:
        await _validate_allocation_target(
            session,
            tenant_id,
            receipt,
            allocation.sales_invoice_id,
            _quantize(allocation.amount),
        )

    unapplied_amount = _quantize(amount_total - applied_total)

    currency = await _resolve_currency(session, tenant_id, receipt.currency_code)
    base_currency = await settings_service.get_base_currency(session, tenant_id)
    fx_rate = _resolve_fx_rate(currency, base_currency, receipt.fx_rate)
    line_fx_rate = fx_rate if currency != base_currency else None
    base_amount_total = _quantize(amount_total * fx_rate)

    ar_account_id = await _get_ar_control_account_id(session, tenant_id)
    credit_account_id = await _get_customer_credit_account_id(session, tenant_id)

    for attempt in range(5):
        try:
            async with _transaction_scope(session):
                locked_result = await session.execute(
                    select(CustomerReceipt)
                    .where(CustomerReceipt.id == receipt_id, CustomerReceipt.tenant_id == tenant_id)
                    .options(lazyload(CustomerReceipt.customer))
                    .with_for_update()
                )
                locked_receipt = locked_result.scalar_one_or_none()
                if not locked_receipt:
                    raise AppException(
                        code="customer_receipt_not_found",
                        message="Receipt not found",
                        http_status=404,
                    )
                if not locked_receipt.receipt_no:
                    locked_receipt.receipt_no = await _ensure_receipt_no(
                        session, tenant_id, locked_receipt.receipt_no
                    )
                receipt_no = locked_receipt.receipt_no

                lines: list[JournalLineCreate] = [
                    JournalLineCreate(
                        account_id=locked_receipt.cash_account_id,
                        debit_amount=amount_total,
                        credit_amount=Decimal("0.00"),
                        line_currency=currency,
                        fx_rate=line_fx_rate,
                        memo=f"Receipt {receipt_no}",
                    )
                ]
                if applied_total > 0:
                    lines.append(
                        JournalLineCreate(
                            account_id=ar_account_id,
                            debit_amount=Decimal("0.00"),
                            credit_amount=applied_total,
                            line_currency=currency,
                            fx_rate=line_fx_rate,
                            memo=f"Receipt {receipt_no}",
                        )
                    )
                if unapplied_amount > 0:
                    lines.append(
                        JournalLineCreate(
                            account_id=credit_account_id,
                            debit_amount=Decimal("0.00"),
                            credit_amount=unapplied_amount,
                            line_currency=currency,
                            fx_rate=line_fx_rate,
                            memo=f"Receipt {receipt_no}",
                        )
                    )

                ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
                entry = await ledger.create_manual_entry(
                    entry_date=locked_receipt.receipt_date,
                    base_currency=base_currency,
                    memo=f"Receipt {receipt_no}",
                    source_type="customer_receipt",
                    source_id=receipt_id,
                    lines=lines,
                    commit=False,
                )
                posted_entry = await ledger.post_entry(entry.id, commit=False)
                locked_receipt.status = CustomerReceiptStatus.POSTED
                locked_receipt.posted_at = posted_entry.posted_at or datetime.now(UTC)
                locked_receipt.posting_journal_entry_id = posted_entry.id
                locked_receipt.currency_code = currency
                locked_receipt.fx_rate = fx_rate
                locked_receipt.base_amount_total = base_amount_total
                receipt = locked_receipt
            break
        except IntegrityError as exc:
            await session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_customer_receipts_tenant_receipt_no" in message:
                receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=True)
                if not receipt:
                    raise
                if receipt.receipt_no:
                    raise AppException(
                        code="customer_receipt_no_exists",
                        message="Receipt number already exists",
                        http_status=409,
                    ) from exc
                continue
            raise

    await session.refresh(receipt)
    return receipt


async def reverse_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    receipt_id: UUID,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> CustomerReceipt:
    receipt = await _get_receipt(session, tenant_id, receipt_id, include_allocations=False)
    if not receipt:
        raise AppException(code="customer_receipt_not_found", message="Receipt not found", http_status=404)

    if receipt.status == CustomerReceiptStatus.REVERSED:
        raise AppException(
            code="customer_receipt_already_reversed",
            message="Receipt has already been reversed",
            http_status=409,
        )
    if receipt.status != CustomerReceiptStatus.POSTED:
        raise AppException(
            code="customer_receipt_not_posted",
            message="Only posted receipts can be reversed",
            http_status=409,
        )
    if receipt.reversal_journal_entry_id:
        raise AppException(
            code="customer_receipt_already_reversed",
            message="Receipt has already been reversed",
            http_status=409,
        )

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=receipt.receipt_date)

    entry = await _find_receipt_entry(session, tenant_id, receipt_id)
    if not entry:
        raise AppException(
            code="customer_receipt_missing_journal_entry",
            message="Posted receipt is missing journal entry",
            http_status=409,
        )
    entry_id = entry.id
    if entry.status == STATUS_REVERSED or entry.is_reversed:
        reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
        receipt.status = CustomerReceiptStatus.REVERSED
        receipt.reversed_at = (
            reversal_entry.posted_at or reversal_entry.posting_date if reversal_entry else datetime.now(UTC)
        )
        if reversal_entry:
            receipt.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(receipt)
        raise AppException(
            code="customer_receipt_already_reversed",
            message="Receipt has already been reversed",
            http_status=409,
        )

    reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
    if reversal_entry:
        receipt.status = CustomerReceiptStatus.REVERSED
        receipt.reversed_at = reversal_entry.posted_at or reversal_entry.posting_date or datetime.now(UTC)
        receipt.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(receipt)
        raise AppException(
            code="customer_receipt_already_reversed",
            message="Receipt has already been reversed",
            http_status=409,
        )

    async with _transaction_scope(session):
        locked_result = await session.execute(
            select(CustomerReceipt)
            .where(CustomerReceipt.id == receipt_id, CustomerReceipt.tenant_id == tenant_id)
            .options(lazyload(CustomerReceipt.customer))
            .with_for_update()
        )
        locked_receipt = locked_result.scalar_one_or_none()
        if not locked_receipt:
            raise AppException(
                code="customer_receipt_not_found",
                message="Receipt not found",
                http_status=404,
            )
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        reversed_entry = await ledger.reverse_entry(entry_id, reason=reason.strip(), commit=False)
        locked_receipt.status = CustomerReceiptStatus.REVERSED
        locked_receipt.reversed_at = reversed_entry.posted_at or datetime.now(UTC)
        locked_receipt.reversal_journal_entry_id = reversed_entry.id
        receipt = locked_receipt

    await session.refresh(receipt)
    return receipt


__all__ = [
    "list_receipts",
    "get_receipt",
    "create_receipt",
    "update_receipt",
    "list_receipt_allocations",
    "add_receipt_allocation",
    "update_receipt_allocation",
    "delete_receipt_allocation",
    "post_receipt",
    "reverse_receipt",
]
