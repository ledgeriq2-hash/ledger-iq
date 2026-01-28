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
from app.models.journal_entry import JournalEntry
from app.models.product import Product, ProductStatus
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceStatus
from app.models.purchase_invoice_line import PurchaseInvoiceLine
from app.models.stock_move import StockMoveDirection, StockMoveSourceType
from app.models.vendor import Vendor, VendorStatus
from app.schemas.journals import JournalLineCreate
from app.services import settings_service, stock_ledger_service
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


def _quantize_rate(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


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
            message="FX rate is required for non-base currency documents",
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


async def _get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppException(code="product_not_found", message="Product not found", http_status=404)
    if getattr(product, "status", None) == ProductStatus.INACTIVE or getattr(product, "is_active", True) is False:
        raise AppException(code="product_inactive", message="Product is inactive", http_status=409)
    return product


async def _get_ap_control_account_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AP_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message="AP control account mapping is missing",
            details={"key": "AP_CONTROL"},
            http_status=422,
        )
    await _get_account(session, tenant_id, mapping.account_id)
    return mapping.account_id


async def _get_input_vat_account_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    keys = ["INPUT_VAT", "INPUT_VAT_ACCOUNT_ID"]
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key.in_(keys),
        )
    )
    mapping = result.scalars().first()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message="Input VAT account mapping is missing",
            details={"keys": keys},
            http_status=422,
        )
    await _get_account(session, tenant_id, mapping.account_id)
    return mapping.account_id


async def _get_vendor(session: AsyncSession, tenant_id: UUID, vendor_id: UUID) -> Vendor:
    result = await session.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise AppException(code="vendor_not_found", message="Vendor not found", http_status=404)
    return vendor


def _normalize_invoice_no(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise AppException(
            code="purchase_invoice_no_required",
            message="Invoice number is required",
            http_status=422,
        )
    return cleaned


async def _next_invoice_no(session: AsyncSession, tenant_id: UUID) -> str:
    prefix = "BILL-"
    pattern = f"^{prefix}\\d{{6}}$"
    result = await session.execute(
        select(func.max(PurchaseInvoice.invoice_no)).where(
            PurchaseInvoice.tenant_id == tenant_id,
            PurchaseInvoice.invoice_no.is_not(None),
            PurchaseInvoice.invoice_no.op("~")(pattern),
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


async def _ensure_invoice_no(session: AsyncSession, tenant_id: UUID, current: str | None) -> str:
    cleaned = (current or "").strip()
    if cleaned:
        return cleaned
    for _ in range(5):
        candidate = await _next_invoice_no(session, tenant_id)
        exists = await session.execute(
            select(PurchaseInvoice.id).where(
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.invoice_no == candidate,
            )
        )
        if exists.scalar_one_or_none():
            continue
        return candidate
    raise AppException(
        code="purchase_invoice_no_conflict",
        message="Unable to generate unique bill number",
        http_status=409,
    )


def _normalize_lines(lines: Sequence[dict[str, Any]], *, require_all: bool) -> list[dict[str, Any]]:
    if not lines:
        raise AppException(
            code="purchase_invoice_lines_required",
            message="Purchase invoice requires at least one line",
            http_status=422,
        )
    normalized: list[dict[str, Any]] = []
    required_fields = {"line_no", "quantity", "unit_price", "expense_account_id"}
    for line in lines:
        if require_all:
            missing = [field for field in required_fields if line.get(field) is None]
            if missing:
                raise AppException(
                    code="purchase_invoice_line_invalid",
                    message="Purchase invoice line is missing required fields",
                    details={"missing": missing, "line_no": line.get("line_no")},
                    http_status=422,
                )
        quantity = line.get("quantity")
        unit_price = line.get("unit_price")
        for label, value in (("quantity", quantity), ("unit_price", unit_price)):
            if value is not None and _quantize(value) < 0:
                raise AppException(
                    code="purchase_invoice_line_invalid",
                    message=f"{label} must be non-negative",
                    http_status=422,
                )
        if quantity is not None and _quantize(quantity) <= 0:
            raise AppException(
                code="purchase_invoice_line_invalid",
                message="quantity must be greater than zero",
                http_status=422,
            )
        computed_amount = _quantize(_quantize(quantity) * _quantize(unit_price))
        provided_amount = line.get("amount")
        if provided_amount is not None and _quantize(provided_amount) != computed_amount:
            raise AppException(
                code="purchase_invoice_line_amount_mismatch",
                message="Line amount must equal quantity * unit_price",
                http_status=422,
            )
        vat_rate = _quantize_rate(line.get("vat_rate"))
        if vat_rate < 0:
            raise AppException(
                code="purchase_invoice_line_invalid",
                message="vat_rate must be non-negative",
                http_status=422,
            )
        vat_amount = _quantize(computed_amount * vat_rate)
        provided_vat_amount = line.get("vat_amount")
        if provided_vat_amount is not None and _quantize(provided_vat_amount) != vat_amount:
            raise AppException(
                code="purchase_invoice_line_vat_mismatch",
                message="vat_amount must equal amount * vat_rate",
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
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "expense_account_id": line.get("expense_account_id"),
            }
        )
    return normalized


def _sum_line_amounts(lines: Sequence[PurchaseInvoiceLine | dict[str, Any]]) -> Decimal:
    total = Decimal("0.00")
    for line in lines:
        amount = line.amount if isinstance(line, PurchaseInvoiceLine) else line.get("amount")
        total += _quantize(amount)
    return total.quantize(Decimal("0.01"))


def _sum_line_vat(lines: Sequence[PurchaseInvoiceLine | dict[str, Any]]) -> Decimal:
    total = Decimal("0.00")
    for line in lines:
        amount = line.vat_amount if isinstance(line, PurchaseInvoiceLine) else line.get("vat_amount")
        total += _quantize(amount)
    return total.quantize(Decimal("0.01"))


def _apply_totals(invoice: PurchaseInvoice, subtotal: Decimal, vat_total: Decimal) -> None:
    subtotal_q = _quantize(subtotal)
    vat_total_q = _quantize(vat_total)
    total_amount = _quantize(subtotal_q + vat_total_q)
    invoice.subtotal = subtotal_q
    invoice.vat_total = vat_total_q
    invoice.total = total_amount
    invoice.total_amount = total_amount


def _apply_base_totals(invoice: PurchaseInvoice, base_subtotal: Decimal, base_vat_total: Decimal) -> None:
    base_subtotal_q = _quantize(base_subtotal)
    base_vat_total_q = _quantize(base_vat_total)
    base_total = _quantize(base_subtotal_q + base_vat_total_q)
    invoice.base_subtotal = base_subtotal_q
    invoice.base_vat_total = base_vat_total_q
    invoice.base_total = base_total


async def _recalculate_totals(session: AsyncSession, invoice: PurchaseInvoice) -> None:
    result = await session.execute(
        select(
            func.coalesce(func.sum(PurchaseInvoiceLine.amount), 0),
            func.coalesce(func.sum(PurchaseInvoiceLine.vat_amount), 0),
        ).where(
            PurchaseInvoiceLine.tenant_id == invoice.tenant_id,
            PurchaseInvoiceLine.invoice_id == invoice.id,
        )
    )
    subtotal_amount, vat_total = result.one()
    subtotal_amount = Decimal(str(subtotal_amount or 0)).quantize(Decimal("0.01"))
    vat_total = Decimal(str(vat_total or 0)).quantize(Decimal("0.01"))
    _apply_totals(invoice, subtotal_amount, vat_total)


async def _replace_lines(
    session: AsyncSession,
    invoice: PurchaseInvoice,
    lines_data: list[dict[str, Any]] | None,
) -> list[PurchaseInvoiceLine]:
    await session.execute(
        delete(PurchaseInvoiceLine).where(
            PurchaseInvoiceLine.invoice_id == invoice.id,
            PurchaseInvoiceLine.tenant_id == invoice.tenant_id,
        )
    )
    created: list[PurchaseInvoiceLine] = []
    if not lines_data:
        return created
    for line in lines_data:
        expense_account_id = line.get("expense_account_id")
        if not expense_account_id:
            raise AppException(
                code="purchase_invoice_line_invalid",
                message="Expense account is required",
                http_status=422,
            )
        await _get_account(session, invoice.tenant_id, expense_account_id)
        if line.get("product_id"):
            await _get_product(session, invoice.tenant_id, line.get("product_id"))
        item = PurchaseInvoiceLine(
            tenant_id=invoice.tenant_id,
            invoice_id=invoice.id,
            line_no=int(line.get("line_no") or 0),
            description=line.get("description"),
            quantity=_quantize(line.get("quantity")),
            product_id=line.get("product_id"),
            unit_id=line.get("unit_id"),
            unit_price=_quantize(line.get("unit_price")),
            amount=_quantize(line.get("amount")),
            vat_rate=_quantize_rate(line.get("vat_rate")),
            vat_amount=_quantize(line.get("vat_amount")),
            expense_account_id=expense_account_id,
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
) -> PurchaseInvoice | None:
    stmt = select(PurchaseInvoice).where(
        PurchaseInvoice.id == invoice_id, PurchaseInvoice.tenant_id == tenant_id
    )
    if include_lines:
        stmt = stmt.options(selectinload(PurchaseInvoice.lines))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_invoice_entry(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "purchase_invoice",
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
    source_type: StockMoveSourceType,
) -> list:
    return await stock_ledger_service.find_moves_by_source(
        session, tenant_id, source_type, invoice_id
    )


async def list_purchase_invoices(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    *,
    vendor_id: UUID | None = None,
    status: PurchaseInvoiceStatus | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[Sequence[PurchaseInvoice], int]:
    page = max(1, page)
    page_size = max(1, page_size)

    query = select(PurchaseInvoice).where(PurchaseInvoice.tenant_id == tenant_id)
    if vendor_id:
        query = query.where(PurchaseInvoice.vendor_id == vendor_id)
    if status:
        try:
            normalized = status if isinstance(status, PurchaseInvoiceStatus) else PurchaseInvoiceStatus(str(status))
        except Exception as exc:
            raise AppException(
                code="purchase_invoice_status_invalid",
                message="Invalid purchase invoice status",
                http_status=422,
            ) from exc
        query = query.where(PurchaseInvoice.status == normalized)
    if date_from:
        query = query.where(PurchaseInvoice.invoice_date >= date_from)
    if date_to:
        query = query.where(PurchaseInvoice.invoice_date <= date_to)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.options(selectinload(PurchaseInvoice.lines))
        .order_by(PurchaseInvoice.invoice_date.desc(), PurchaseInvoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_purchase_invoice(
    session: AsyncSession, tenant_id: UUID, invoice_id: UUID
) -> PurchaseInvoice | None:
    return await _get_invoice(session, tenant_id, invoice_id, include_lines=True)


async def list_purchase_invoice_lines(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
) -> list[PurchaseInvoiceLine]:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)
    result = await session.execute(
        select(PurchaseInvoiceLine)
        .where(PurchaseInvoiceLine.tenant_id == tenant_id, PurchaseInvoiceLine.invoice_id == invoice_id)
        .order_by(PurchaseInvoiceLine.line_no.asc(), PurchaseInvoiceLine.id.asc())
    )
    return list(result.scalars().all())


async def add_purchase_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    payload: Any,
) -> PurchaseInvoiceLine:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)
    if invoice.status != PurchaseInvoiceStatus.DRAFT:
        raise AppException(
            code="purchase_invoice_not_editable",
            message="Only draft purchase invoices can be edited",
            http_status=409,
        )

    data = _to_dict(payload)
    line_no = data.get("line_no")
    if line_no is None:
        existing_max = max((line.line_no for line in invoice.lines), default=0)
        line_no = existing_max + 1
    existing_line = await session.execute(
        select(PurchaseInvoiceLine.id).where(
            PurchaseInvoiceLine.tenant_id == tenant_id,
            PurchaseInvoiceLine.invoice_id == invoice_id,
            PurchaseInvoiceLine.line_no == line_no,
        )
    )
    if existing_line.scalar_one_or_none():
        raise AppException(
            code="purchase_invoice_line_exists",
            message="Purchase invoice line number already exists",
            http_status=409,
        )

    quantity = data.get("quantity")
    unit_price = data.get("unit_price")
    if quantity is None or unit_price is None:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="Quantity and unit price are required",
            http_status=422,
        )
    if _quantize(quantity) <= 0:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="quantity must be greater than zero",
            http_status=422,
        )
    if _quantize(unit_price) < 0:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="unit_price must be non-negative",
            http_status=422,
        )
    amount = _quantize(_quantize(quantity) * _quantize(unit_price))
    provided_amount = data.get("amount")
    if provided_amount is not None and _quantize(provided_amount) != amount:
        raise AppException(
            code="purchase_invoice_line_amount_mismatch",
            message="Line amount must equal quantity * unit_price",
            http_status=422,
        )
    vat_rate = _quantize_rate(data.get("vat_rate"))
    if vat_rate < 0:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="vat_rate must be non-negative",
            http_status=422,
        )
    vat_amount = _quantize(amount * vat_rate)
    provided_vat_amount = data.get("vat_amount")
    if provided_vat_amount is not None and _quantize(provided_vat_amount) != vat_amount:
        raise AppException(
            code="purchase_invoice_line_vat_mismatch",
            message="vat_amount must equal amount * vat_rate",
            http_status=422,
        )

    expense_account_id = data.get("expense_account_id")
    if not expense_account_id:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="Expense account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, expense_account_id)

    if data.get("product_id"):
        await _get_product(session, tenant_id, data.get("product_id"))

    line = PurchaseInvoiceLine(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        line_no=int(line_no),
        description=data.get("description"),
        quantity=_quantize(quantity),
        product_id=data.get("product_id"),
        unit_id=data.get("unit_id"),
        unit_price=_quantize(unit_price),
        amount=amount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        expense_account_id=expense_account_id,
    )
    session.add(line)
    await session.flush()
    await _recalculate_totals(session, invoice)
    await session.commit()
    await session.refresh(line)
    return line


async def update_purchase_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    line_id: UUID,
    payload: Any,
) -> PurchaseInvoiceLine:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)
    if invoice.status != PurchaseInvoiceStatus.DRAFT:
        raise AppException(
            code="purchase_invoice_not_editable",
            message="Only draft purchase invoices can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(PurchaseInvoiceLine).where(
            PurchaseInvoiceLine.tenant_id == tenant_id,
            PurchaseInvoiceLine.invoice_id == invoice_id,
            PurchaseInvoiceLine.id == line_id,
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        raise AppException(
            code="purchase_invoice_line_not_found",
            message="Purchase invoice line not found",
            http_status=404,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "line_no" in data and data["line_no"] is not None:
        existing = await session.execute(
            select(PurchaseInvoiceLine.id).where(
                PurchaseInvoiceLine.tenant_id == tenant_id,
                PurchaseInvoiceLine.invoice_id == invoice_id,
                PurchaseInvoiceLine.line_no == data["line_no"],
                PurchaseInvoiceLine.id != line_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="purchase_invoice_line_exists",
                message="Purchase invoice line number already exists",
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
            code="purchase_invoice_line_invalid",
            message="quantity must be greater than zero",
            http_status=422,
        )
    if _quantize(unit_price) < 0:
        raise AppException(
            code="purchase_invoice_line_invalid",
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
                code="purchase_invoice_line_amount_mismatch",
                message="Line amount must equal quantity * unit_price",
                http_status=422,
            )

    vat_rate = _quantize_rate(data.get("vat_rate", line.vat_rate))
    if vat_rate < 0:
        raise AppException(
            code="purchase_invoice_line_invalid",
            message="vat_rate must be non-negative",
            http_status=422,
        )
    vat_amount = _quantize(line.amount * vat_rate)
    if "vat_amount" in data and data.get("vat_amount") is not None:
        provided_vat_amount = _quantize(data.get("vat_amount"))
        if provided_vat_amount != vat_amount:
            raise AppException(
                code="purchase_invoice_line_vat_mismatch",
                message="vat_amount must equal amount * vat_rate",
                http_status=422,
            )
    line.vat_rate = vat_rate
    line.vat_amount = vat_amount

    if "expense_account_id" in data and data["expense_account_id"] is not None:
        await _get_account(session, tenant_id, data["expense_account_id"])
        line.expense_account_id = data["expense_account_id"]

    await session.flush()
    await _recalculate_totals(session, invoice)
    await session.commit()
    await session.refresh(line)
    return line


async def delete_purchase_invoice_line(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    line_id: UUID,
) -> bool:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)
    if invoice.status != PurchaseInvoiceStatus.DRAFT:
        raise AppException(
            code="purchase_invoice_not_editable",
            message="Only draft purchase invoices can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(PurchaseInvoiceLine).where(
            PurchaseInvoiceLine.tenant_id == tenant_id,
            PurchaseInvoiceLine.invoice_id == invoice_id,
            PurchaseInvoiceLine.id == line_id,
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


async def create_purchase_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
) -> PurchaseInvoice:
    data = _to_dict(payload)
    raw_invoice_no = data.get("invoice_no") or data.get("bill_no")
    invoice_no = _normalize_invoice_no(raw_invoice_no) if raw_invoice_no else None
    vendor_id = data.get("vendor_id")
    if not vendor_id:
        raise AppException(code="vendor_id_required", message="Vendor is required", http_status=422)
    await _get_vendor(session, tenant_id, vendor_id)
    invoice_date = data.get("invoice_date")
    if not invoice_date:
        raise AppException(code="invoice_date_required", message="Invoice date is required", http_status=422)

    lines_data = data.get("lines") or []
    normalized_lines = _normalize_lines(lines_data, require_all=True)
    subtotal_amount = _sum_line_amounts(normalized_lines)
    vat_total = _sum_line_vat(normalized_lines)
    total_amount = _quantize(subtotal_amount + vat_total)
    if total_amount <= 0:
        raise AppException(
            code="purchase_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )

    if invoice_no:
        existing = await session.execute(
            select(PurchaseInvoice.id).where(
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.invoice_no == invoice_no,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="purchase_invoice_no_exists",
                message="Invoice number already exists",
                http_status=409,
            )

    invoice = PurchaseInvoice(
        tenant_id=tenant_id,
        vendor_id=vendor_id,
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        due_date=data.get("due_date"),
        currency_code=data.get("currency_code"),
        fx_rate=_quantize_fx(data.get("fx_rate")) if data.get("fx_rate") is not None else None,
        memo=data.get("memo"),
        status=PurchaseInvoiceStatus.DRAFT,
        subtotal=subtotal_amount,
        vat_total=vat_total,
        total=total_amount,
        total_amount=total_amount,
    )

    async with _transaction_scope(session):
        session.add(invoice)
        await session.flush()
        await _replace_lines(session, invoice, normalized_lines)
        _apply_totals(invoice, subtotal_amount, vat_total)
    await session.refresh(invoice)
    return invoice


async def update_purchase_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    payload: Any,
) -> PurchaseInvoice | None:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        return None
    if invoice.status != PurchaseInvoiceStatus.DRAFT:
        raise AppException(
            code="purchase_invoice_not_editable",
            message="Only draft purchase invoices can be edited",
            http_status=409,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "invoice_no" in data:
        if data["invoice_no"] is None:
            invoice.invoice_no = None
        else:
            invoice_no = _normalize_invoice_no(data["invoice_no"])
            existing = await session.execute(
                select(PurchaseInvoice.id).where(
                    PurchaseInvoice.tenant_id == tenant_id,
                    PurchaseInvoice.invoice_no == invoice_no,
                    PurchaseInvoice.id != invoice_id,
                )
            )
            if existing.scalar_one_or_none():
                raise AppException(
                    code="purchase_invoice_no_exists",
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
    if "fx_rate" in data:
        invoice.fx_rate = _quantize_fx(data.get("fx_rate")) if data.get("fx_rate") is not None else None
    if "memo" in data:
        invoice.memo = data.get("memo")
    if "vendor_id" in data and data["vendor_id"] is not None:
        await _get_vendor(session, tenant_id, data["vendor_id"])
        invoice.vendor_id = data["vendor_id"]

    if "lines" in data and data["lines"] is not None:
        normalized_lines = _normalize_lines(data["lines"], require_all=True)
        await _replace_lines(session, invoice, normalized_lines)
        subtotal_amount = _sum_line_amounts(normalized_lines)
        vat_total = _sum_line_vat(normalized_lines)
        _apply_totals(invoice, subtotal_amount, vat_total)

    await session.commit()
    await session.refresh(invoice)
    return invoice


async def post_purchase_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> PurchaseInvoice:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)

    if invoice.status == PurchaseInvoiceStatus.POSTED:
        raise AppException(
            code="purchase_invoice_already_posted",
            message="Purchase invoice has already been posted",
            http_status=409,
        )
    if invoice.status == PurchaseInvoiceStatus.REVERSED:
        raise AppException(
            code="purchase_invoice_not_draft",
            message="Only draft purchase invoices can be posted",
            http_status=409,
        )
    if invoice.posting_journal_entry_id:
        raise AppException(
            code="purchase_invoice_already_posted",
            message="Purchase invoice has already been posted",
            http_status=409,
        )

    invoice_id = invoice.id
    invoice_date = invoice.invoice_date
    currency_code = invoice.currency_code
    entry_date = invoice_date

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=invoice_date)

    vendor = await _get_vendor(session, tenant_id, invoice.vendor_id)
    if vendor.status == VendorStatus.INACTIVE:
        raise AppException(
            code="vendor_inactive",
            message="Vendor is inactive",
            http_status=409,
        )

    existing_entry = await _find_invoice_entry(session, tenant_id, invoice_id)
    if existing_entry and existing_entry.status == STATUS_POSTED:
        invoice.status = PurchaseInvoiceStatus.POSTED
        invoice.posted_at = existing_entry.posted_at or existing_entry.posting_date or datetime.now(UTC)
        invoice.posting_journal_entry_id = existing_entry.id
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="purchase_invoice_already_posted",
            message="Purchase invoice has already been posted",
            http_status=409,
        )

    if not invoice.lines:
        raise AppException(
            code="purchase_invoice_lines_required",
            message="Purchase invoice requires at least one line",
            http_status=422,
        )
    subtotal_amount = _sum_line_amounts(invoice.lines)
    vat_total = _sum_line_vat(invoice.lines)
    total_amount = _quantize(subtotal_amount + vat_total)
    if total_amount <= 0:
        raise AppException(
            code="purchase_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )

    existing_moves = await _find_stock_moves(session, tenant_id, invoice_id, StockMoveSourceType.PURCHASE)
    if existing_moves:
        raise AppException(
            code="purchase_invoice_stock_exists",
            message="Stock moves already exist for this purchase invoice",
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
                code="purchase_invoice_line_quantity_invalid",
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
        stock_payloads.append(
            {
                "product_id": product.id,
                "quantity": line_quantity,
                "unit_id": unit_id,
            }
        )

    ap_account_id = await _get_ap_control_account_id(session, tenant_id)
    currency = await _resolve_currency(session, tenant_id, currency_code)
    base_currency = await settings_service.get_base_currency(session, tenant_id)
    fx_rate = _resolve_fx_rate(currency, base_currency, invoice.fx_rate)
    line_fx_rate = fx_rate if currency != base_currency else None
    input_vat_account_id: UUID | None = None
    if vat_total > 0:
        input_vat_account_id = await _get_input_vat_account_id(session, tenant_id)

    expense_totals: dict[UUID, Decimal] = {}
    for line in invoice.lines:
        await _get_account(session, tenant_id, line.expense_account_id)
        expense_totals[line.expense_account_id] = expense_totals.get(
            line.expense_account_id, Decimal("0.00")
        ) + _quantize(line.amount)

    for attempt in range(5):
        try:
            async with _transaction_scope(session):
                locked_result = await session.execute(
                    select(PurchaseInvoice)
                    .where(PurchaseInvoice.id == invoice_id, PurchaseInvoice.tenant_id == tenant_id)
                    .options(lazyload(PurchaseInvoice.vendor))
                    .with_for_update()
                )
                locked_invoice = locked_result.scalar_one_or_none()
                if not locked_invoice:
                    raise AppException(
                        code="purchase_invoice_not_found",
                        message="Purchase invoice not found",
                        http_status=404,
                    )
                entry = existing_entry
                if not locked_invoice.invoice_no:
                    locked_invoice.invoice_no = await _ensure_invoice_no(
                        session, tenant_id, locked_invoice.invoice_no
                    )
                invoice_no = locked_invoice.invoice_no
                lines = [
                    JournalLineCreate(
                        account_id=ap_account_id,
                        debit_amount=Decimal("0.00"),
                        credit_amount=total_amount,
                        line_currency=currency,
                        fx_rate=line_fx_rate,
                        memo=f"Purchase invoice {invoice_no}",
                    )
                ]
                for account_id, amount in expense_totals.items():
                    lines.append(
                        JournalLineCreate(
                            account_id=account_id,
                            debit_amount=_quantize(amount),
                            credit_amount=Decimal("0.00"),
                            line_currency=currency,
                            fx_rate=line_fx_rate,
                            memo=f"Purchase invoice {invoice_no}",
                        )
                    )
                if vat_total > 0 and input_vat_account_id:
                    lines.append(
                        JournalLineCreate(
                            account_id=input_vat_account_id,
                            debit_amount=_quantize(vat_total),
                            credit_amount=Decimal("0.00"),
                            line_currency=currency,
                            fx_rate=line_fx_rate,
                            memo=f"Purchase invoice {invoice_no} VAT",
                        )
                    )
                ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
                if entry and entry.status != STATUS_POSTED:
                    posted_entry = await ledger.post_entry(entry.id, commit=False)
                else:
                    entry = await ledger.create_manual_entry(
                        entry_date=entry_date,
                        base_currency=base_currency,
                        memo=f"Purchase invoice {invoice_no}",
                        source_type="purchase_invoice",
                        source_id=invoice_id,
                        lines=lines,
                        commit=False,
                    )
                    posted_entry = await ledger.post_entry(entry.id, commit=False)
                for payload in stock_payloads:
                    await stock_ledger_service.create_stock_move(
                        session,
                        tenant_id,
                        {
                            **payload,
                            "direction": StockMoveDirection.IN,
                            "source_type": StockMoveSourceType.PURCHASE,
                            "source_id": invoice_id,
                            "posting_journal_entry_id": posted_entry.id,
                            "posted_at": posted_entry.posted_at or datetime.now(UTC),
                        },
                        commit=False,
                    )
                locked_invoice.status = PurchaseInvoiceStatus.POSTED
                locked_invoice.posted_at = posted_entry.posted_at or datetime.now(UTC)
                locked_invoice.posting_journal_entry_id = posted_entry.id
                locked_invoice.currency_code = currency
                locked_invoice.fx_rate = fx_rate
                _apply_totals(locked_invoice, subtotal_amount, vat_total)
                _apply_base_totals(
                    locked_invoice,
                    _quantize(subtotal_amount * fx_rate),
                    _quantize(vat_total * fx_rate),
                )
                line_result = await session.execute(
                    select(PurchaseInvoiceLine).where(
                        PurchaseInvoiceLine.tenant_id == tenant_id,
                        PurchaseInvoiceLine.invoice_id == invoice_id,
                    )
                )
                for line in line_result.scalars().all():
                    line.base_amount = _quantize(line.amount * fx_rate)
                invoice = locked_invoice
            break
        except IntegrityError as exc:
            await session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_purchase_invoices_tenant_invoice_no" in message:
                invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=True)
                if not invoice:
                    raise
                if invoice.invoice_no:
                    raise AppException(
                        code="purchase_invoice_no_exists",
                        message="Invoice number already exists",
                        http_status=409,
                    ) from exc
                continue
            raise

    await session.refresh(invoice)
    return invoice


async def reverse_purchase_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> PurchaseInvoice:
    invoice = await _get_invoice(session, tenant_id, invoice_id, include_lines=False)
    if not invoice:
        raise AppException(code="purchase_invoice_not_found", message="Purchase invoice not found", http_status=404)

    if invoice.status == PurchaseInvoiceStatus.REVERSED:
        raise AppException(
            code="purchase_invoice_already_reversed",
            message="Purchase invoice has already been reversed",
            http_status=409,
        )
    if invoice.status != PurchaseInvoiceStatus.POSTED:
        raise AppException(
            code="purchase_invoice_not_posted",
            message="Only posted purchase invoices can be reversed",
            http_status=409,
        )
    if invoice.reversal_journal_entry_id:
        raise AppException(
            code="purchase_invoice_already_reversed",
            message="Purchase invoice has already been reversed",
            http_status=409,
        )

    invoice_id = invoice.id
    invoice_date = invoice.invoice_date

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=invoice_date)

    entry = await _find_invoice_entry(session, tenant_id, invoice_id)
    if not entry:
        raise AppException(
            code="purchase_invoice_missing_journal_entry",
            message="Posted purchase invoice is missing journal entry",
            http_status=409,
        )
    entry_id = entry.id
    if entry.status == STATUS_REVERSED or entry.is_reversed:
        reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
        invoice.status = PurchaseInvoiceStatus.REVERSED
        invoice.reversed_at = (
            reversal_entry.posted_at or reversal_entry.posting_date if reversal_entry else datetime.now(UTC)
        )
        if reversal_entry:
            invoice.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="purchase_invoice_already_reversed",
            message="Purchase invoice has already been reversed",
            http_status=409,
        )

    reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
    if reversal_entry:
        invoice.status = PurchaseInvoiceStatus.REVERSED
        invoice.reversed_at = reversal_entry.posted_at or reversal_entry.posting_date or datetime.now(UTC)
        invoice.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(invoice)
        raise AppException(
            code="purchase_invoice_already_reversed",
            message="Purchase invoice has already been reversed",
            http_status=409,
        )

    async with _transaction_scope(session):
        locked_result = await session.execute(
            select(PurchaseInvoice)
            .where(PurchaseInvoice.id == invoice_id, PurchaseInvoice.tenant_id == tenant_id)
            .options(lazyload(PurchaseInvoice.vendor))
            .with_for_update()
        )
        locked_invoice = locked_result.scalar_one_or_none()
        if not locked_invoice:
            raise AppException(
                code="purchase_invoice_not_found",
                message="Purchase invoice not found",
                http_status=404,
            )
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        reversed_entry = await ledger.reverse_entry(entry_id, reason=reason.strip(), commit=False)
        stock_moves = await _find_stock_moves(session, tenant_id, invoice_id, StockMoveSourceType.PURCHASE)
        if stock_moves:
            await stock_ledger_service.create_reversal_moves(
                session,
                tenant_id,
                source_id=invoice_id,
                original_moves=stock_moves,
                posting_journal_entry_id=reversed_entry.id,
                posted_at=reversed_entry.posted_at or datetime.now(UTC),
            )
        locked_invoice.status = PurchaseInvoiceStatus.REVERSED
        locked_invoice.reversed_at = reversed_entry.posted_at or datetime.now(UTC)
        locked_invoice.reversal_journal_entry_id = reversed_entry.id
        invoice = locked_invoice

    await session.refresh(invoice)
    return invoice


__all__ = [
    "list_purchase_invoices",
    "get_purchase_invoice",
    "create_purchase_invoice",
    "update_purchase_invoice",
    "list_purchase_invoice_lines",
    "add_purchase_invoice_line",
    "update_purchase_invoice_line",
    "delete_purchase_invoice_line",
    "post_purchase_invoice",
    "reverse_purchase_invoice",
]
