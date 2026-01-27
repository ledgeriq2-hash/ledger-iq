from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.core.exceptions import AppException
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.customer import Customer, CustomerStatus
from app.models.journal_entry import JournalEntry
from app.models.product import Product, ProductStatus
from app.models.sales_invoice import SalesInvoice, SalesInvoiceStatus
from app.models.sales_invoice_line import SalesInvoiceLine
from app.models.stock_move import StockMove, StockMoveDirection
from app.schemas.journals import JournalLineCreate
from app.services.ledger_service import DEFAULT_BASE_CURRENCY, LedgerService, STATUS_POSTED, STATUS_REVERSED
from app.services.period_guard import PeriodGuard
from app.services import settings_service, stock_service
from app.services.unit_conversion_service import resolve_multiplier


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _quantize(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


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
    settings = await settings_service.get_settings(session, tenant_id)
    fallback = (settings.currency or "").strip().upper()
    return fallback or DEFAULT_BASE_CURRENCY


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


async def _get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppException(code="product_not_found", message="Product not found", http_status=404)
    if getattr(product, "status", None) == ProductStatus.INACTIVE:
        raise AppException(code="product_inactive", message="Product is inactive", http_status=409)
    return product


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


async def _get_customer(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalar_one_or_none()
    if not customer or customer.status == CustomerStatus.DELETED:
        raise AppException(code="customer_not_found", message="Customer not found", http_status=404)
    return customer


def _normalize_invoice_no(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise AppException(code="sales_invoice_no_required", message="Invoice number is required", http_status=422)
    return cleaned


async def _next_invoice_no(session: AsyncSession, tenant_id: UUID) -> str:
    prefix = "INV-"
    pattern = f"^{prefix}\\d{{6}}$"
    result = await session.execute(
        select(func.max(SalesInvoice.invoice_no)).where(
            SalesInvoice.tenant_id == tenant_id,
            SalesInvoice.invoice_no.is_not(None),
            SalesInvoice.invoice_no.op("~")(pattern),
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


async def _ensure_invoice_no(
    session: AsyncSession, tenant_id: UUID, current: str | None
) -> str:
    cleaned = (current or "").strip()
    if cleaned:
        return cleaned
    for _ in range(5):
        candidate = await _next_invoice_no(session, tenant_id)
        exists = await session.execute(
            select(SalesInvoice.id).where(SalesInvoice.tenant_id == tenant_id, SalesInvoice.invoice_no == candidate)
        )
        if exists.scalar_one_or_none():
            continue
        return candidate
    raise AppException(
        code="sales_invoice_no_conflict",
        message="Unable to generate unique invoice number",
        http_status=409,
    )


def _normalize_lines(lines: Sequence[dict[str, Any]], *, require_all: bool) -> list[dict[str, Any]]:
    if not lines:
        raise AppException(
            code="sales_invoice_lines_required",
            message="Sales invoice requires at least one line",
            http_status=422,
        )
    normalized: list[dict[str, Any]] = []
    required_fields = {"line_no", "quantity", "unit_price", "revenue_account_id"}
    for line in lines:
        if require_all:
            missing = [field for field in required_fields if line.get(field) is None]
            if missing:
                raise AppException(
                    code="sales_invoice_line_invalid",
                    message="Sales invoice line is missing required fields",
                    details={"missing": missing, "line_no": line.get("line_no")},
                    http_status=422,
                )
        quantity = line.get("quantity")
        unit_price = line.get("unit_price")
        for label, value in (("quantity", quantity), ("unit_price", unit_price)):
            if value is not None and _quantize(value) < 0:
                raise AppException(
                    code="sales_invoice_line_invalid",
                    message=f"{label} must be non-negative",
                    http_status=422,
                )
        if quantity is not None and _quantize(quantity) <= 0:
            raise AppException(
                code="sales_invoice_line_invalid",
                message="quantity must be greater than zero",
                http_status=422,
            )
        computed_amount = _quantize(_quantize(quantity) * _quantize(unit_price))
        provided_amount = line.get("amount")
        if provided_amount is not None and _quantize(provided_amount) != computed_amount:
            raise AppException(
                code="sales_invoice_line_amount_mismatch",
                message="Line amount must equal quantity * unit_price",
                http_status=422,
            )
        normalized.append(
            {
                "line_no": line.get("line_no"),
                "description": line.get("description"),
                "quantity": _quantize(quantity),
                "product_id": line.get("product_id"),
                "unit_id": line.get("unit_id"),
                "unit_price": _quantize(unit_price),
                "amount": computed_amount,
                "revenue_account_id": line.get("revenue_account_id"),
            }
        )
    return normalized


def _sum_line_amounts(lines: Sequence[SalesInvoiceLine | dict[str, Any]]) -> Decimal:
    total = Decimal("0.00")
    for line in lines:
        amount = line.amount if isinstance(line, SalesInvoiceLine) else line.get("amount")
        total += _quantize(amount)
    return total.quantize(Decimal("0.01"))


def _apply_totals(invoice: SalesInvoice, total_amount: Decimal) -> None:
    invoice.subtotal = total_amount
    invoice.total = total_amount
    invoice.total_amount = total_amount


async def _recalculate_totals(session: AsyncSession, invoice: SalesInvoice) -> None:
    result = await session.execute(
        select(func.coalesce(func.sum(SalesInvoiceLine.amount), 0)).where(
            SalesInvoiceLine.tenant_id == invoice.tenant_id,
            SalesInvoiceLine.invoice_id == invoice.id,
        )
    )
    total_amount = Decimal(str(result.scalar_one() or 0)).quantize(Decimal("0.01"))
    _apply_totals(invoice, total_amount)


async def _replace_lines(
    session: AsyncSession,
    invoice: SalesInvoice,
    lines_data: list[dict[str, Any]] | None,
) -> list[SalesInvoiceLine]:
    await session.execute(
        delete(SalesInvoiceLine).where(
            SalesInvoiceLine.invoice_id == invoice.id,
            SalesInvoiceLine.tenant_id == invoice.tenant_id,
        )
    )
    created: list[SalesInvoiceLine] = []
    if not lines_data:
        return created
    for line in lines_data:
        revenue_account_id = line.get("revenue_account_id")
        if not revenue_account_id:
            raise AppException(
                code="sales_invoice_line_invalid",
                message="Revenue account is required",
                http_status=422,
            )
        await _get_account(session, invoice.tenant_id, revenue_account_id)
        item = SalesInvoiceLine(
            tenant_id=invoice.tenant_id,
            invoice_id=invoice.id,
            line_no=int(line.get("line_no") or 0),
            description=line.get("description"),
            quantity=_quantize(line.get("quantity")),
            product_id=line.get("product_id"),
            unit_id=line.get("unit_id"),
            unit_price=_quantize(line.get("unit_price")),
            amount=_quantize(line.get("amount")),
            revenue_account_id=revenue_account_id,
        )
        session.add(item)
        created.append(item)
    return created


async def _get_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    include_lines: bool = True,
) -> SalesInvoice | None:
    stmt = select(SalesInvoice).where(SalesInvoice.id == invoice_id, SalesInvoice.tenant_id == tenant_id)
    if include_lines:
        stmt = stmt.options(selectinload(SalesInvoice.lines))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_invoice_entry(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "sales_invoice",
            JournalEntry.source_id == invoice_id,
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


async def _find_stock_moves(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    reference_type: str,
) -> list[StockMove]:
    result = await session.execute(
        select(StockMove).where(
            StockMove.tenant_id == tenant_id,
            StockMove.reference_type == reference_type,
            StockMove.reference_id == invoice_id,
        )
    )
    return list(result.scalars().all())


async def list_sales_invoices(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    *,
    customer_id: UUID | None = None,
    status: SalesInvoiceStatus | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[Sequence[SalesInvoice], int]:
    page = max(1, page)
    page_size = max(1, page_size)

    query = select(SalesInvoice).where(SalesInvoice.tenant_id == tenant_id)
    if customer_id:
        query = query.where(SalesInvoice.customer_id == customer_id)
    if status:
        try:
            normalized = status if isinstance(status, SalesInvoiceStatus) else SalesInvoiceStatus(str(status))
        except Exception as exc:
            raise AppException(
                code="sales_invoice_status_invalid",
                message="Invalid sales invoice status",
                http_status=422,
            ) from exc
        query = query.where(SalesInvoice.status == normalized)
    if date_from:
        query = query.where(SalesInvoice.invoice_date >= date_from)
    if date_to:
        query = query.where(SalesInvoice.invoice_date <= date_to)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.options(selectinload(SalesInvoice.lines))
        .order_by(SalesInvoice.invoice_date.desc(), SalesInvoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_sales_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> SalesInvoice | None:
    return await _get_invoice(session, tenant_id, invoice_id, include_lines=True)


async def create_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
) -> SalesInvoice:
    data = _to_dict(payload)
    raw_invoice_no = data.get("invoice_no")
    invoice_no = _normalize_invoice_no(raw_invoice_no) if raw_invoice_no else None
    customer_id = data.get("customer_id")
    if not customer_id:
        raise AppException(code="customer_id_required", message="Customer is required", http_status=422)
    await _get_customer(session, tenant_id, customer_id)
    invoice_date = data.get("invoice_date")
    if not invoice_date:
        raise AppException(code="invoice_date_required", message="Invoice date is required", http_status=422)

    lines_data = data.get("lines") or []
    normalized_lines = _normalize_lines(lines_data, require_all=True)
    total_amount = _sum_line_amounts(normalized_lines)
    if total_amount <= 0:
        raise AppException(
            code="sales_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )

    if invoice_no:
        existing = await session.execute(
            select(SalesInvoice.id).where(
                SalesInvoice.tenant_id == tenant_id,
                SalesInvoice.invoice_no == invoice_no,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="sales_invoice_no_exists",
                message="Invoice number already exists",
                http_status=409,
            )

    invoice = SalesInvoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        due_date=data.get("due_date"),
        currency_code=data.get("currency_code"),
        memo=data.get("memo"),
        status=SalesInvoiceStatus.DRAFT,
        subtotal=total_amount,
        total=total_amount,
        total_amount=total_amount,
    )

    async with _transaction_scope(session):
        session.add(invoice)
        await session.flush()
        await _replace_lines(session, invoice, normalized_lines)
        _apply_totals(invoice, _sum_line_amounts(normalized_lines))
    await session.refresh(invoice)
    return invoice


async def update_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    payload: Any,
) -> SalesInvoice | None:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        return None
    if invoice.status != SalesInvoiceStatus.DRAFT:
        raise AppException(
            code="sales_invoice_not_editable",
            message="Only draft sales invoices can be edited",
            http_status=409,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "invoice_no" in data and data["invoice_no"] is not None:
        invoice_no = _normalize_invoice_no(data["invoice_no"])
        existing = await session.execute(
            select(SalesInvoice.id).where(
                SalesInvoice.tenant_id == tenant_id,
                SalesInvoice.invoice_no == invoice_no,
                SalesInvoice.id != invoice_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="sales_invoice_no_exists",
                message="Invoice number already exists",
                http_status=409,
            )
        invoice.invoice_no = invoice_no
    if "invoice_date" in data and data["invoice_date"] is not None:
        invoice.invoice_date = data["invoice_date"]
    if "due_date" in data:
        invoice.due_date = data.get("due_date")
    if "currency_code" in data:
        invoice.currency_code = data.get("currency_code")
    if "memo" in data:
        invoice.memo = data.get("memo")
    if "customer_id" in data and data["customer_id"] is not None:
        await _get_customer(session, tenant_id, data["customer_id"])
        invoice.customer_id = data["customer_id"]

    if "lines" in data and data["lines"] is not None:
        normalized_lines = _normalize_lines(data["lines"], require_all=True)
        await _replace_lines(session, invoice, normalized_lines)
        _apply_totals(invoice, _sum_line_amounts(normalized_lines))

    await session.commit()
    await session.refresh(invoice)
    return invoice


async def list_sales_invoice_lines(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
) -> list[SalesInvoiceLine]:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)
    result = await session.execute(
        select(SalesInvoiceLine)
        .where(SalesInvoiceLine.tenant_id == tenant_id, SalesInvoiceLine.invoice_id == invoice_id)
        .order_by(SalesInvoiceLine.line_no.asc(), SalesInvoiceLine.id.asc())
    )
    return list(result.scalars().all())


async def add_sales_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    payload: Any,
) -> SalesInvoiceLine:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)
    if invoice.status != SalesInvoiceStatus.DRAFT:
        raise AppException(
            code="sales_invoice_not_editable",
            message="Only draft sales invoices can be edited",
            http_status=409,
        )

    data = _to_dict(payload)
    line_no = data.get("line_no")
    if line_no is None:
        existing_max = max((line.line_no for line in invoice.lines), default=0)
        line_no = existing_max + 1
    existing_line = await session.execute(
        select(SalesInvoiceLine.id).where(
            SalesInvoiceLine.tenant_id == tenant_id,
            SalesInvoiceLine.invoice_id == invoice_id,
            SalesInvoiceLine.line_no == line_no,
        )
    )
    if existing_line.scalar_one_or_none():
        raise AppException(
            code="sales_invoice_line_exists",
            message="Sales invoice line number already exists",
            http_status=409,
        )

    quantity = data.get("quantity")
    unit_price = data.get("unit_price")
    if quantity is None or unit_price is None:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="Quantity and unit price are required",
            http_status=422,
        )
    if _quantize(quantity) <= 0:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="quantity must be greater than zero",
            http_status=422,
        )
    if _quantize(unit_price) < 0:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="unit_price must be non-negative",
            http_status=422,
        )
    amount = _quantize(_quantize(quantity) * _quantize(unit_price))
    provided_amount = data.get("amount")
    if provided_amount is not None and _quantize(provided_amount) != amount:
        raise AppException(
            code="sales_invoice_line_amount_mismatch",
            message="Line amount must equal quantity * unit_price",
            http_status=422,
        )

    revenue_account_id = data.get("revenue_account_id")
    if not revenue_account_id:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="Revenue account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, revenue_account_id)

    if data.get("product_id"):
        await _get_product(session, tenant_id, data.get("product_id"))

    line = SalesInvoiceLine(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        line_no=int(line_no),
        description=data.get("description"),
        quantity=_quantize(quantity),
        product_id=data.get("product_id"),
        unit_id=data.get("unit_id"),
        unit_price=_quantize(unit_price),
        amount=amount,
        revenue_account_id=revenue_account_id,
    )
    session.add(line)
    await session.flush()
    await _recalculate_totals(session, invoice)
    await session.commit()
    await session.refresh(line)
    return line


async def update_sales_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    line_id: UUID,
    payload: Any,
) -> SalesInvoiceLine:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)
    if invoice.status != SalesInvoiceStatus.DRAFT:
        raise AppException(
            code="sales_invoice_not_editable",
            message="Only draft sales invoices can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(SalesInvoiceLine).where(
            SalesInvoiceLine.tenant_id == tenant_id,
            SalesInvoiceLine.invoice_id == invoice_id,
            SalesInvoiceLine.id == line_id,
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        raise AppException(
            code="sales_invoice_line_not_found",
            message="Sales invoice line not found",
            http_status=404,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "line_no" in data and data["line_no"] is not None:
        existing = await session.execute(
            select(SalesInvoiceLine.id).where(
                SalesInvoiceLine.tenant_id == tenant_id,
                SalesInvoiceLine.invoice_id == invoice_id,
                SalesInvoiceLine.line_no == data["line_no"],
                SalesInvoiceLine.id != line_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="sales_invoice_line_exists",
                message="Sales invoice line number already exists",
                http_status=409,
            )
        line.line_no = int(data["line_no"])

    if "description" in data:
        line.description = data.get("description")
    if "product_id" in data:
        product_id = data.get("product_id")
        if product_id:
            await _get_product(session, tenant_id, product_id)
        line.product_id = product_id
    if "unit_id" in data:
        line.unit_id = data.get("unit_id")

    quantity = data.get("quantity", line.quantity)
    unit_price = data.get("unit_price", line.unit_price)
    if _quantize(quantity) <= 0:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="quantity must be greater than zero",
            http_status=422,
        )
    if _quantize(unit_price) < 0:
        raise AppException(
            code="sales_invoice_line_invalid",
            message="unit_price must be non-negative",
            http_status=422,
        )
    line.quantity = _quantize(quantity)
    line.unit_price = _quantize(unit_price)
    line.amount = _quantize(line.quantity * line.unit_price)

    if "amount" in data and data.get("amount") is not None:
        provided_amount = _quantize(data.get("amount"))
        if provided_amount != line.amount:
            raise AppException(
                code="sales_invoice_line_amount_mismatch",
                message="Line amount must equal quantity * unit_price",
                http_status=422,
            )

    if "revenue_account_id" in data and data["revenue_account_id"] is not None:
        await _get_account(session, tenant_id, data["revenue_account_id"])
        line.revenue_account_id = data["revenue_account_id"]

    await session.flush()
    await _recalculate_totals(session, invoice)
    await session.commit()
    await session.refresh(line)
    return line


async def delete_sales_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    line_id: UUID,
) -> bool:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)
    if invoice.status != SalesInvoiceStatus.DRAFT:
        raise AppException(
            code="sales_invoice_not_editable",
            message="Only draft sales invoices can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(SalesInvoiceLine).where(
            SalesInvoiceLine.tenant_id == tenant_id,
            SalesInvoiceLine.invoice_id == invoice_id,
            SalesInvoiceLine.id == line_id,
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        return False
    await session.delete(line)
    await session.flush()
    await _recalculate_totals(session, invoice)
    await session.commit()
    return True


async def post_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> SalesInvoice:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)

    if invoice.status == SalesInvoiceStatus.POSTED:
        raise AppException(
            code="sales_invoice_already_posted",
            message="Sales invoice has already been posted",
            http_status=409,
        )
    if invoice.status == SalesInvoiceStatus.REVERSED:
        raise AppException(
            code="sales_invoice_not_draft",
            message="Only draft sales invoices can be posted",
            http_status=409,
        )
    if invoice.posting_journal_entry_id:
        raise AppException(
            code="sales_invoice_already_posted",
            message="Sales invoice has already been posted",
            http_status=409,
        )

    invoice_id = invoice.id
    invoice_date = invoice.invoice_date
    currency_code = invoice.currency_code
    entry_date = invoice_date

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=invoice_date)

    customer = await _get_customer(session, tenant_id, invoice.customer_id)
    if customer.status == CustomerStatus.INACTIVE:
        raise AppException(
            code="customer_inactive",
            message="Customer is inactive",
            http_status=409,
        )
    if customer.status == CustomerStatus.DELETED:
        raise AppException(
            code="customer_deleted",
            message="Customer is deleted",
            http_status=409,
        )

    existing_entry = await _find_invoice_entry(session, tenant_id, invoice_id)
    if existing_entry and existing_entry.status == STATUS_POSTED:
        invoice.status = SalesInvoiceStatus.POSTED
        invoice.posted_at = existing_entry.posted_at or existing_entry.posting_date or datetime.now(UTC)
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="sales_invoice_already_posted",
            message="Sales invoice has already been posted",
            http_status=409,
        )

    if not invoice.lines:
        raise AppException(
            code="sales_invoice_lines_required",
            message="Sales invoice requires at least one line",
            http_status=422,
        )
    total_amount = _sum_line_amounts(invoice.lines)
    if total_amount <= 0:
        raise AppException(
            code="sales_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )

    existing_moves = await _find_stock_moves(session, tenant_id, invoice_id, "sales_invoice")
    if existing_moves:
        raise AppException(
            code="sales_invoice_stock_exists",
            message="Stock moves already exist for this sales invoice",
            http_status=409,
        )

    stock_payloads: list[dict[str, Any]] = []
    product_cache: dict[UUID, Product] = {}
    for line in invoice.lines:
        if not line.product_id:
            continue
        line_quantity = _quantize(line.quantity)
        if line_quantity <= 0:
            raise AppException(
                code="sales_invoice_line_quantity_invalid",
                message="Line quantity must be greater than zero",
                http_status=422,
            )
        product = product_cache.get(line.product_id)
        if not product:
            product = await _get_product(session, tenant_id, line.product_id)
            product_cache[product.id] = product
        base_unit_id = product.base_unit_id
        if not base_unit_id:
            raise AppException(
                code="product_base_unit_required",
                message="Product base unit is required for inventory posting",
                http_status=422,
            )
        unit_id = line.unit_id or base_unit_id
        if unit_id == base_unit_id:
            quantity_base = line_quantity
        else:
            multiplier = await resolve_multiplier(session, tenant_id, unit_id, base_unit_id)
            quantity_base = _quantize(line_quantity * multiplier)
        stock_payloads.append(
            {
                "product_id": product.id,
                "move_date": invoice_date,
                "direction": StockMoveDirection.OUT,
                "quantity_base": quantity_base,
                "unit_id": unit_id,
                "quantity_original": line_quantity,
                "reference_type": "sales_invoice",
                "reference_id": invoice_id,
            }
        )

    ar_account_id = await _get_ar_control_account_id(session, tenant_id)
    currency = await _resolve_currency(session, tenant_id, currency_code)

    revenue_totals: dict[UUID, Decimal] = {}
    for line in invoice.lines:
        await _get_account(session, tenant_id, line.revenue_account_id)
        revenue_totals[line.revenue_account_id] = revenue_totals.get(line.revenue_account_id, Decimal("0.00")) + _quantize(
            line.amount
        )

    for attempt in range(5):
        try:
            async with _transaction_scope(session):
                locked_result = await session.execute(
                    select(SalesInvoice)
                    .where(SalesInvoice.id == invoice_id, SalesInvoice.tenant_id == tenant_id)
                    .options(lazyload(SalesInvoice.customer))
                    .with_for_update()
                )
                locked_invoice = locked_result.scalar_one_or_none()
                if not locked_invoice:
                    raise AppException(
                        code="sales_invoice_not_found",
                        message="Sales invoice not found",
                        http_status=404,
                    )
                entry = existing_entry
                if not locked_invoice.invoice_no:
                    locked_invoice.invoice_no = await _ensure_invoice_no(
                        session, tenant_id, locked_invoice.invoice_no
                    )
                invoice_no = locked_invoice.invoice_no
                lines: list[JournalLineCreate] = [
                    JournalLineCreate(
                        account_id=ar_account_id,
                        debit_amount=total_amount,
                        credit_amount=Decimal("0.00"),
                        line_currency=currency,
                        memo=f"Sales invoice {invoice_no}",
                    )
                ]
                for account_id, amount in revenue_totals.items():
                    lines.append(
                        JournalLineCreate(
                            account_id=account_id,
                            debit_amount=Decimal("0.00"),
                            credit_amount=_quantize(amount),
                            line_currency=currency,
                            memo=f"Sales invoice {invoice_no}",
                        )
                    )
                ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
                if entry and entry.status != STATUS_POSTED:
                    posted_entry = await ledger.post_entry(entry.id, commit=False)
                else:
                    entry = await ledger.create_manual_entry(
                        entry_date=entry_date,
                        base_currency=currency,
                        memo=f"Sales invoice {invoice_no}",
                        source_type="sales_invoice",
                        source_id=invoice_id,
                        lines=lines,
                        commit=False,
                    )
                    posted_entry = await ledger.post_entry(entry.id, commit=False)
                for payload in stock_payloads:
                    await stock_service.record_move(session, tenant_id, payload, commit=False)
                locked_invoice.status = SalesInvoiceStatus.POSTED
                locked_invoice.posted_at = posted_entry.posted_at or datetime.now(UTC)
                locked_invoice.posting_journal_entry_id = posted_entry.id
                _apply_totals(locked_invoice, total_amount)
                invoice = locked_invoice
            break
        except IntegrityError as exc:
            await session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_sales_invoices_tenant_invoice_no" in message:
                invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
                if not invoice:
                    raise
                if invoice.invoice_no:
                    raise AppException(
                        code="sales_invoice_no_exists",
                        message="Invoice number already exists",
                        http_status=409,
                    ) from exc
                continue
            raise

    await session.refresh(invoice)
    return invoice


async def reverse_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> SalesInvoice:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="sales_invoice_not_found", message="Sales invoice not found", http_status=404)

    if invoice.status == SalesInvoiceStatus.REVERSED:
        raise AppException(
            code="sales_invoice_already_reversed",
            message="Sales invoice has already been reversed",
            http_status=409,
        )
    if invoice.status != SalesInvoiceStatus.POSTED:
        raise AppException(
            code="sales_invoice_not_posted",
            message="Only posted sales invoices can be reversed",
            http_status=409,
        )
    if invoice.reversal_journal_entry_id:
        raise AppException(
            code="sales_invoice_already_reversed",
            message="Sales invoice has already been reversed",
            http_status=409,
        )

    invoice_id = invoice.id
    invoice_date = invoice.invoice_date

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=invoice_date)

    entry = await _find_invoice_entry(session, tenant_id, invoice_id)
    if not entry:
        raise AppException(
            code="sales_invoice_missing_journal_entry",
            message="Posted sales invoice is missing journal entry",
            http_status=409,
        )
    entry_id = entry.id
    if entry.status == STATUS_REVERSED or entry.is_reversed:
        invoice.status = SalesInvoiceStatus.REVERSED
        invoice.reversed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="sales_invoice_already_reversed",
            message="Sales invoice has already been reversed",
            http_status=409,
        )

    reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
    if reversal_entry:
        invoice.status = SalesInvoiceStatus.REVERSED
        invoice.reversed_at = reversal_entry.posted_at or reversal_entry.posting_date or datetime.now(UTC)
        invoice.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="sales_invoice_already_reversed",
            message="Sales invoice has already been reversed",
            http_status=409,
        )

    stock_moves = await _find_stock_moves(session, tenant_id, invoice_id, "sales_invoice")
    reversal_moves = await _find_stock_moves(session, tenant_id, invoice_id, "sales_invoice_reverse")
    move_payloads = [
        (move.product_id, _quantize(move.quantity_base), move.unit_id, move.quantity_original)
        for move in stock_moves
    ]

    async with _transaction_scope(session):
        locked_result = await session.execute(
            select(SalesInvoice)
            .where(SalesInvoice.id == invoice_id, SalesInvoice.tenant_id == tenant_id)
            .options(lazyload(SalesInvoice.customer))
            .with_for_update()
        )
        locked_invoice = locked_result.scalar_one_or_none()
        if not locked_invoice:
            raise AppException(
                code="sales_invoice_not_found",
                message="Sales invoice not found",
                http_status=404,
            )
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        reversed_entry = await ledger.reverse_entry(entry_id, reason=reason.strip(), commit=False)
        if move_payloads and not reversal_moves:
            for product_id, quantity_base, unit_id, quantity_original in move_payloads:
                await stock_service.record_move(
                    session,
                    tenant_id,
                    {
                        "product_id": product_id,
                        "move_date": invoice_date,
                        "direction": StockMoveDirection.IN,
                        "quantity_base": quantity_base,
                        "unit_id": unit_id,
                        "quantity_original": quantity_original,
                        "reference_type": "sales_invoice_reverse",
                        "reference_id": invoice_id,
                    },
                    commit=False,
                )
        locked_invoice.status = SalesInvoiceStatus.REVERSED
        locked_invoice.reversed_at = reversed_entry.posted_at or datetime.now(UTC)
        locked_invoice.reversal_journal_entry_id = reversed_entry.id
        invoice = locked_invoice

    await session.refresh(invoice)
    return invoice


__all__ = [
    "list_sales_invoices",
    "get_sales_invoice",
    "create_sales_invoice",
    "update_sales_invoice",
    "list_sales_invoice_lines",
    "add_sales_invoice_line",
    "update_sales_invoice_line",
    "delete_sales_invoice_line",
    "post_sales_invoice",
    "reverse_sales_invoice",
]
