from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.customer_receipt import CustomerReceipt, CustomerReceiptStatus
from app.models.customer_receipt_allocation import CustomerReceiptAllocation
from app.models.fx_revaluation_line import FXRevaluationLine
from app.models.fx_revaluation_run import FXRevaluationRun, FXRevaluationStatus
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceStatus
from app.models.sales_invoice import SalesInvoice, SalesInvoiceStatus
from app.models.vendor_payment import VendorPayment, VendorPaymentStatus
from app.models.vendor_payment_allocation import VendorPaymentAllocation
from app.schemas.journals import JournalLineCreate
from app.services.ledger_service import LedgerService
from app.services.period_guard import PeriodGuard
from app.services import settings_service


def _quantize(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _quantize_fx(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.000001"))


def _parse_period_id(period_id: str) -> tuple[int, int]:
    cleaned = (period_id or "").strip()
    if not cleaned:
        raise AppException(code="fx_revaluation_period_required", message="period_id is required", http_status=422)
    if len(cleaned) == 7 and cleaned[4] == "-":
        year = int(cleaned[:4])
        month = int(cleaned[5:])
        if month < 1 or month > 12:
            raise AppException(
                code="fx_revaluation_period_invalid",
                message="period_id must be YYYY-MM or ISO date",
                http_status=422,
            )
        return year, month
    try:
        parsed = date.fromisoformat(cleaned)
        if parsed.month < 1 or parsed.month > 12:
            raise AppException(
                code="fx_revaluation_period_invalid",
                message="period_id must be YYYY-MM or ISO date",
                http_status=422,
            )
        return parsed.year, parsed.month
    except Exception as exc:  # noqa: BLE001
        raise AppException(
            code="fx_revaluation_period_invalid",
            message="period_id must be YYYY-MM or ISO date",
            http_status=422,
        ) from exc


def _period_end_date(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


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


async def _get_mapping_account_id(
    session: AsyncSession, tenant_id: UUID, keys: Sequence[str], *, message: str
) -> UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key.in_(list(keys)),
        )
    )
    mapping = result.scalars().first()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message=message,
            details={"keys": list(keys)},
            http_status=422,
        )
    await _get_account(session, tenant_id, mapping.account_id)
    return mapping.account_id


async def _load_allocations_by_invoice(
    session: AsyncSession, tenant_id: UUID, invoice_ids: list[UUID]
) -> dict[UUID, Decimal]:
    if not invoice_ids:
        return {}
    result = await session.execute(
        select(
            CustomerReceiptAllocation.sales_invoice_id,
            func.coalesce(func.sum(CustomerReceiptAllocation.amount), 0),
        )
        .join(CustomerReceipt, CustomerReceiptAllocation.receipt_id == CustomerReceipt.id)
        .where(
            CustomerReceiptAllocation.tenant_id == tenant_id,
            CustomerReceiptAllocation.sales_invoice_id.in_(invoice_ids),
            CustomerReceipt.status == CustomerReceiptStatus.POSTED,
        )
        .group_by(CustomerReceiptAllocation.sales_invoice_id)
    )
    return {row[0]: _quantize(row[1]) for row in result.all()}


async def _load_allocations_by_bill(
    session: AsyncSession, tenant_id: UUID, bill_ids: list[UUID]
) -> dict[UUID, Decimal]:
    if not bill_ids:
        return {}
    result = await session.execute(
        select(
            VendorPaymentAllocation.purchase_bill_id,
            func.coalesce(func.sum(VendorPaymentAllocation.amount), 0),
        )
        .join(VendorPayment, VendorPaymentAllocation.payment_id == VendorPayment.id)
        .where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.purchase_bill_id.in_(bill_ids),
            VendorPayment.status == VendorPaymentStatus.POSTED,
        )
        .group_by(VendorPaymentAllocation.purchase_bill_id)
    )
    return {row[0]: _quantize(row[1]) for row in result.all()}


async def list_runs(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[Sequence[FXRevaluationRun], int]:
    page = max(1, page)
    page_size = max(1, page_size)

    query = select(FXRevaluationRun).where(FXRevaluationRun.tenant_id == tenant_id)
    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.order_by(FXRevaluationRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_run(session: AsyncSession, tenant_id: UUID, run_id: UUID) -> FXRevaluationRun | None:
    result = await session.execute(
        select(FXRevaluationRun)
        .where(FXRevaluationRun.id == run_id, FXRevaluationRun.tenant_id == tenant_id)
        .options(selectinload(FXRevaluationRun.lines))
    )
    return result.scalar_one_or_none()


async def run_revaluation(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> FXRevaluationRun:
    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload or {})
    period_year, period_month = _parse_period_id(str(data.get("period_id") or ""))
    currency = (data.get("currency") or "").strip().upper()
    if not currency:
        raise AppException(code="fx_revaluation_currency_required", message="currency is required", http_status=422)
    reval_fx_rate = _quantize_fx(data.get("reval_fx_rate"))
    if reval_fx_rate <= 0:
        raise AppException(
            code="fx_revaluation_fx_rate_invalid",
            message="reval_fx_rate must be greater than zero",
            http_status=422,
        )

    base_currency = await settings_service.get_base_currency(session, tenant_id)
    if currency == base_currency:
        raise AppException(
            code="fx_revaluation_currency_invalid",
            message="Revaluation currency must be different from base currency",
            http_status=422,
        )

    existing = await session.execute(
        select(FXRevaluationRun.id).where(
            FXRevaluationRun.tenant_id == tenant_id,
            FXRevaluationRun.period_year == period_year,
            FXRevaluationRun.period_month == period_month,
            FXRevaluationRun.currency_code == currency,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="fx_revaluation_already_exists",
            message="FX revaluation already exists for this period and currency",
            http_status=409,
        )

    reval_date = _period_end_date(period_year, period_month)
    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=reval_date)

    ar_account_id = await _get_mapping_account_id(
        session,
        tenant_id,
        ["AR_CONTROL"],
        message="AR control account mapping is missing",
    )
    ap_account_id = await _get_mapping_account_id(
        session,
        tenant_id,
        ["AP_CONTROL"],
        message="AP control account mapping is missing",
    )
    fx_gain_account_id = await _get_mapping_account_id(
        session,
        tenant_id,
        ["FX_GAIN", "FX_GAIN_ACCOUNT_ID"],
        message="FX gain account mapping is missing",
    )
    fx_loss_account_id = await _get_mapping_account_id(
        session,
        tenant_id,
        ["FX_LOSS", "FX_LOSS_ACCOUNT_ID"],
        message="FX loss account mapping is missing",
    )

    invoices_result = await session.execute(
        select(SalesInvoice).where(
            SalesInvoice.tenant_id == tenant_id,
            SalesInvoice.status == SalesInvoiceStatus.POSTED,
            SalesInvoice.currency_code == currency,
        )
    )
    invoices = list(invoices_result.scalars().all())
    invoice_allocations = await _load_allocations_by_invoice(session, tenant_id, [inv.id for inv in invoices])

    bills_result = await session.execute(
        select(PurchaseInvoice).where(
            PurchaseInvoice.tenant_id == tenant_id,
            PurchaseInvoice.status == PurchaseInvoiceStatus.POSTED,
            PurchaseInvoice.currency_code == currency,
        )
    )
    bills = list(bills_result.scalars().all())
    bill_allocations = await _load_allocations_by_bill(session, tenant_id, [bill.id for bill in bills])

    lines: list[FXRevaluationLine] = []
    ar_delta_total = Decimal("0.00")
    ap_delta_total = Decimal("0.00")

    for invoice in invoices:
        total = _quantize(invoice.total)
        allocated = _quantize(invoice_allocations.get(invoice.id, Decimal("0.00")))
        remaining = _quantize(total - allocated)
        if remaining <= 0:
            continue
        if not invoice.fx_rate:
            raise AppException(
                code="fx_revaluation_fx_rate_missing",
                message="Posted invoice missing fx_rate",
                http_status=409,
            )
        old_base_remaining = _quantize(remaining * _quantize_fx(invoice.fx_rate))
        new_base_remaining = _quantize(remaining * reval_fx_rate)
        delta = _quantize(new_base_remaining - old_base_remaining)
        if delta == 0:
            continue
        ar_delta_total += delta
        lines.append(
            FXRevaluationLine(
                tenant_id=tenant_id,
                source_type="AR",
                source_id=invoice.id,
                foreign_remaining=remaining,
                old_base_remaining=old_base_remaining,
                new_base_remaining=new_base_remaining,
                delta_base=delta,
            )
        )

    for bill in bills:
        total = _quantize(bill.total)
        allocated = _quantize(bill_allocations.get(bill.id, Decimal("0.00")))
        remaining = _quantize(total - allocated)
        if remaining <= 0:
            continue
        if not bill.fx_rate:
            raise AppException(
                code="fx_revaluation_fx_rate_missing",
                message="Posted bill missing fx_rate",
                http_status=409,
            )
        old_base_remaining = _quantize(remaining * _quantize_fx(bill.fx_rate))
        new_base_remaining = _quantize(remaining * reval_fx_rate)
        delta = _quantize(new_base_remaining - old_base_remaining)
        if delta == 0:
            continue
        ap_delta_total += delta
        lines.append(
            FXRevaluationLine(
                tenant_id=tenant_id,
                source_type="AP",
                source_id=bill.id,
                foreign_remaining=remaining,
                old_base_remaining=old_base_remaining,
                new_base_remaining=new_base_remaining,
                delta_base=delta,
            )
        )

    if not lines:
        raise AppException(
            code="fx_revaluation_no_delta",
            message="No revaluation required for the selected period and currency",
            http_status=409,
        )

    journal_lines: list[JournalLineCreate] = []
    if ar_delta_total != 0:
        if ar_delta_total > 0:
            journal_lines.append(
                JournalLineCreate(
                    account_id=ar_account_id,
                    debit_amount=_quantize(ar_delta_total),
                    credit_amount=Decimal("0.00"),
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AR",
                )
            )
            journal_lines.append(
                JournalLineCreate(
                    account_id=fx_gain_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=_quantize(ar_delta_total),
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AR gain",
                )
            )
        else:
            delta_abs = _quantize(abs(ar_delta_total))
            journal_lines.append(
                JournalLineCreate(
                    account_id=fx_loss_account_id,
                    debit_amount=delta_abs,
                    credit_amount=Decimal("0.00"),
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AR loss",
                )
            )
            journal_lines.append(
                JournalLineCreate(
                    account_id=ar_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=delta_abs,
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AR",
                )
            )

    if ap_delta_total != 0:
        if ap_delta_total > 0:
            delta_abs = _quantize(ap_delta_total)
            journal_lines.append(
                JournalLineCreate(
                    account_id=fx_loss_account_id,
                    debit_amount=delta_abs,
                    credit_amount=Decimal("0.00"),
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AP loss",
                )
            )
            journal_lines.append(
                JournalLineCreate(
                    account_id=ap_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=delta_abs,
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AP",
                )
            )
        else:
            delta_abs = _quantize(abs(ap_delta_total))
            journal_lines.append(
                JournalLineCreate(
                    account_id=ap_account_id,
                    debit_amount=delta_abs,
                    credit_amount=Decimal("0.00"),
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AP",
                )
            )
            journal_lines.append(
                JournalLineCreate(
                    account_id=fx_gain_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=delta_abs,
                    line_currency=base_currency,
                    memo=f"FX revaluation {currency} AP gain",
                )
            )

    if not journal_lines:
        raise AppException(
            code="fx_revaluation_no_delta",
            message="No revaluation required for the selected period and currency",
            http_status=409,
        )

    run = FXRevaluationRun(
        tenant_id=tenant_id,
        period_year=period_year,
        period_month=period_month,
        currency_code=currency,
        reval_fx_rate=reval_fx_rate,
        status=FXRevaluationStatus.POSTED,
    )

    ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)

    try:
        session.add(run)
        await session.flush()
        for line in lines:
            line.run_id = run.id
            session.add(line)
        entry = await ledger.create_manual_entry(
            entry_date=reval_date,
            base_currency=base_currency,
            memo=f"FX revaluation {currency} {period_year}-{period_month:02d}",
            source_type="fx_revaluation",
            source_id=run.id,
            lines=journal_lines,
            commit=False,
        )
        posted_entry = await ledger.post_entry(entry.id, commit=False)
        run.posting_journal_entry_id = posted_entry.id
        run.status = FXRevaluationStatus.POSTED
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppException(
            code="fx_revaluation_conflict",
            message="Unable to create FX revaluation run",
            http_status=409,
        ) from exc

    await session.refresh(run)
    return run


__all__ = ["list_runs", "get_run", "run_revaluation"]
