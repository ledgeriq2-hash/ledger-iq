from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.journal_entry import JournalEntry
from app.models.product import Product, ProductStatus
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceStatus
from app.models.purchase_invoice_line import PurchaseInvoiceLine
from app.models.stock_move import StockMove, StockMoveDirection
from app.models.vendor import Vendor
from app.schemas.journals import JournalLineCreate
from app.services import settings_service, stock_service
from app.services.ledger_service import DEFAULT_BASE_CURRENCY, LedgerService, STATUS_POSTED, STATUS_REVERSED
from app.services.period_guard import PeriodGuard
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


def _normalize_lines(lines: Sequence[dict[str, Any]], *, require_all: bool) -> list[dict[str, Any]]:
    if not lines:
        raise AppException(
            code="purchase_invoice_lines_required",
            message="Purchase invoice requires at least one line",
            http_status=422,
        )
    normalized: list[dict[str, Any]] = []
    required_fields = {"line_no", "quantity", "unit_price", "amount", "expense_account_id"}
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
        amount = line.get("amount")
        quantity = line.get("quantity")
        unit_price = line.get("unit_price")
        for label, value in (("amount", amount), ("quantity", quantity), ("unit_price", unit_price)):
            if value is not None and _quantize(value) < 0:
                raise AppException(
                    code="purchase_invoice_line_invalid",
                    message=f"{label} must be non-negative",
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
                "amount": _quantize(amount),
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


async def create_purchase_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
) -> PurchaseInvoice:
    data = _to_dict(payload)
    invoice_no = _normalize_invoice_no(data.get("invoice_no") or "")
    vendor_id = data.get("vendor_id")
    if not vendor_id:
        raise AppException(code="vendor_id_required", message="Vendor is required", http_status=422)
    await _get_vendor(session, tenant_id, vendor_id)
    invoice_date = data.get("invoice_date")
    if not invoice_date:
        raise AppException(code="invoice_date_required", message="Invoice date is required", http_status=422)

    lines_data = data.get("lines") or []
    normalized_lines = _normalize_lines(lines_data, require_all=True)
    total_amount = _sum_line_amounts(normalized_lines)
    if total_amount <= 0:
        raise AppException(
            code="purchase_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )

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
        currency_code=data.get("currency_code"),
        status=PurchaseInvoiceStatus.DRAFT,
        total_amount=total_amount,
    )

    async with _transaction_scope(session):
        session.add(invoice)
        await session.flush()
        await _replace_lines(session, invoice, normalized_lines)
        invoice.total_amount = _sum_line_amounts(normalized_lines)
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
    if "invoice_no" in data and data["invoice_no"] is not None:
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
    if "currency_code" in data:
        invoice.currency_code = data.get("currency_code")
    if "vendor_id" in data and data["vendor_id"] is not None:
        await _get_vendor(session, tenant_id, data["vendor_id"])
        invoice.vendor_id = data["vendor_id"]

    if "lines" in data and data["lines"] is not None:
        normalized_lines = _normalize_lines(data["lines"], require_all=True)
        await _replace_lines(session, invoice, normalized_lines)
        invoice.total_amount = _sum_line_amounts(normalized_lines)

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
        return invoice
    if invoice.status == PurchaseInvoiceStatus.REVERSED:
        raise AppException(
            code="purchase_invoice_not_draft",
            message="Only draft purchase invoices can be posted",
            http_status=409,
        )

    invoice_id = invoice.id
    invoice_date = invoice.invoice_date
    invoice_no = invoice.invoice_no
    currency_code = invoice.currency_code
    entry_date = invoice_date

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=invoice_date)
    existing_entry = await _find_invoice_entry(session, tenant_id, invoice_id)
    if existing_entry and existing_entry.status == STATUS_POSTED:
        invoice.status = PurchaseInvoiceStatus.POSTED
        invoice.posted_at = existing_entry.posted_at or existing_entry.posting_date or datetime.now(UTC)
        await session.commit()
        await session.refresh(invoice)
        return invoice

    if not invoice.lines:
        raise AppException(
            code="purchase_invoice_lines_required",
            message="Purchase invoice requires at least one line",
            http_status=422,
        )
    total_amount = _sum_line_amounts(invoice.lines)
    if total_amount <= 0:
        raise AppException(
            code="purchase_invoice_total_invalid",
            message="Invoice total must be greater than zero",
            http_status=422,
        )
    if _quantize(invoice.total_amount) != total_amount:
        raise AppException(
            code="purchase_invoice_total_mismatch",
            message="Invoice total does not match line amounts",
            http_status=409,
        )

    existing_moves = await _find_stock_moves(session, tenant_id, invoice_id, "purchase_invoice")
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
            raise AppException(
                code="purchase_invoice_line_product_required",
                message="Product is required to post purchase invoice",
                http_status=422,
            )
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
        if unit_id == base_unit_id:
            quantity_base = line_quantity
        else:
            multiplier = await resolve_multiplier(session, tenant_id, unit_id, base_unit_id)
            quantity_base = _quantize(line_quantity * multiplier)
        stock_payloads.append(
            {
                "product_id": product.id,
                "move_date": invoice_date,
                "direction": StockMoveDirection.IN,
                "quantity_base": quantity_base,
                "unit_id": unit_id,
                "quantity_original": line_quantity,
                "reference_type": "purchase_invoice",
                "reference_id": invoice_id,
            }
        )

    ap_account_id = await _get_ap_control_account_id(session, tenant_id)
    currency = await _resolve_currency(session, tenant_id, currency_code)

    lines: list[JournalLineCreate] = [
        JournalLineCreate(
            account_id=ap_account_id,
            debit_amount=Decimal("0.00"),
            credit_amount=total_amount,
            line_currency=currency,
            memo=f"Purchase invoice {invoice_no}",
        )
    ]
    for line in invoice.lines:
        await _get_account(session, tenant_id, line.expense_account_id)
        lines.append(
            JournalLineCreate(
                account_id=line.expense_account_id,
                debit_amount=_quantize(line.amount),
                credit_amount=Decimal("0.00"),
                line_currency=currency,
                memo=f"Purchase invoice {invoice_no}",
            )
        )

    async with _transaction_scope(session):
        entry = existing_entry
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        if entry and entry.status != STATUS_POSTED:
            posted_entry = await ledger.post_entry(entry.id, commit=False)
        else:
            entry = await ledger.create_manual_entry(
                entry_date=entry_date,
                base_currency=currency,
                memo=f"Purchase invoice {invoice_no}",
                source_type="purchase_invoice",
                source_id=invoice_id,
                lines=lines,
                commit=False,
            )
            posted_entry = await ledger.post_entry(entry.id, commit=False)
        for payload in stock_payloads:
            await stock_service.record_move(session, tenant_id, payload, commit=False)
        invoice.status = PurchaseInvoiceStatus.POSTED
        invoice.posted_at = posted_entry.posted_at or datetime.now(UTC)
        invoice.total_amount = total_amount

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
        return invoice
    if invoice.status != PurchaseInvoiceStatus.POSTED:
        raise AppException(
            code="purchase_invoice_not_posted",
            message="Only posted purchase invoices can be reversed",
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
    if entry.status == STATUS_REVERSED or entry.is_reversed:
        invoice.status = PurchaseInvoiceStatus.REVERSED
        invoice.reversed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(invoice)
        return invoice

    reversal_entry = await _find_reversal_entry(session, tenant_id, entry.id)
    if reversal_entry:
        invoice.status = PurchaseInvoiceStatus.REVERSED
        invoice.reversed_at = reversal_entry.posted_at or reversal_entry.posting_date or datetime.now(UTC)
        await session.commit()
        await session.refresh(invoice)
        return invoice

    stock_moves = await _find_stock_moves(session, tenant_id, invoice_id, "purchase_invoice")
    reversal_moves = await _find_stock_moves(session, tenant_id, invoice_id, "purchase_invoice_reverse")

    async with _transaction_scope(session):
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        reversed_entry = await ledger.reverse_entry(entry.id, reason=reason.strip(), commit=False)
        if stock_moves and not reversal_moves:
            for move in stock_moves:
                await stock_service.record_move(
                    session,
                    tenant_id,
                    {
                        "product_id": move.product_id,
                        "move_date": invoice_date,
                        "direction": StockMoveDirection.OUT,
                        "quantity_base": _quantize(move.quantity_base),
                        "unit_id": move.unit_id,
                        "quantity_original": move.quantity_original,
                        "reference_type": "purchase_invoice_reverse",
                        "reference_id": invoice_id,
                    },
                    commit=False,
                )
        invoice.status = PurchaseInvoiceStatus.REVERSED
        invoice.reversed_at = reversed_entry.posted_at or datetime.now(UTC)

    await session.refresh(invoice)
    return invoice


__all__ = [
    "list_purchase_invoices",
    "get_purchase_invoice",
    "create_purchase_invoice",
    "update_purchase_invoice",
    "post_purchase_invoice",
    "reverse_purchase_invoice",
]
