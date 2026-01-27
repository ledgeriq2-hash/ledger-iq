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
from app.models.journal_entry import JournalEntry
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceStatus
from app.models.vendor import Vendor, VendorStatus
from app.models.vendor_payment import VendorPayment, VendorPaymentStatus
from app.models.vendor_payment_allocation import VendorPaymentAllocation
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


async def _get_vendor_prepay_account_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "VENDOR_PREPAY",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AppException(
            code="account_mapping_missing",
            message="Vendor prepayment account mapping is missing",
            details={"key": "VENDOR_PREPAY"},
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


def _normalize_payment_no(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise AppException(code="vendor_payment_no_required", message="Payment number is required", http_status=422)
    return cleaned


async def _next_payment_no(session: AsyncSession, tenant_id: UUID) -> str:
    prefix = "PAY-"
    pattern = f"^{prefix}\\d{{6}}$"
    result = await session.execute(
        select(func.max(VendorPayment.payment_no)).where(
            VendorPayment.tenant_id == tenant_id,
            VendorPayment.payment_no.is_not(None),
            VendorPayment.payment_no.op("~")(pattern),
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


async def _ensure_payment_no(session: AsyncSession, tenant_id: UUID, current: str | None) -> str:
    cleaned = (current or "").strip()
    if cleaned:
        return cleaned
    for _ in range(5):
        candidate = await _next_payment_no(session, tenant_id)
        exists = await session.execute(
            select(VendorPayment.id).where(
                VendorPayment.tenant_id == tenant_id,
                VendorPayment.payment_no == candidate,
            )
        )
        if exists.scalar_one_or_none():
            continue
        return candidate
    raise AppException(
        code="vendor_payment_no_conflict",
        message="Unable to generate unique payment number",
        http_status=409,
    )


async def _get_payment(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    *,
    include_allocations: bool = True,
) -> VendorPayment | None:
    stmt = select(VendorPayment).where(
        VendorPayment.id == payment_id, VendorPayment.tenant_id == tenant_id
    )
    if include_allocations:
        stmt = stmt.options(selectinload(VendorPayment.allocations))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_bill(session: AsyncSession, tenant_id: UUID, bill_id: UUID) -> PurchaseInvoice | None:
    result = await session.execute(
        select(PurchaseInvoice).where(PurchaseInvoice.id == bill_id, PurchaseInvoice.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _bill_total(bill: PurchaseInvoice) -> Decimal:
    total = getattr(bill, "total", None)
    if total is None:
        total = bill.total_amount
    return _quantize(total)


async def _sum_payment_allocations(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(VendorPaymentAllocation.amount), 0)).where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.payment_id == payment_id,
        )
    )
    return _quantize(result.scalar_one() or 0)


async def _sum_posted_bill_allocations(
    session: AsyncSession, tenant_id: UUID, bill_id: UUID
) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(VendorPaymentAllocation.amount), 0))
        .join(VendorPayment, VendorPaymentAllocation.payment_id == VendorPayment.id)
        .where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.purchase_bill_id == bill_id,
            VendorPayment.status == VendorPaymentStatus.POSTED,
        )
    )
    return _quantize(result.scalar_one() or 0)


async def _find_payment_entry(
    session: AsyncSession, tenant_id: UUID, payment_id: UUID
) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "vendor_payment",
            JournalEntry.source_id == payment_id,
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


async def list_payments(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    *,
    vendor_id: UUID | None = None,
    status: VendorPaymentStatus | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[Sequence[VendorPayment], int]:
    page = max(1, page)
    page_size = max(1, page_size)

    query = select(VendorPayment).where(VendorPayment.tenant_id == tenant_id)
    if vendor_id:
        query = query.where(VendorPayment.vendor_id == vendor_id)
    if status:
        try:
            normalized = status if isinstance(status, VendorPaymentStatus) else VendorPaymentStatus(str(status))
        except Exception as exc:
            raise AppException(
                code="vendor_payment_status_invalid",
                message="Invalid vendor payment status",
                http_status=422,
            ) from exc
        query = query.where(VendorPayment.status == normalized)
    if date_from:
        query = query.where(VendorPayment.payment_date >= date_from)
    if date_to:
        query = query.where(VendorPayment.payment_date <= date_to)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.options(selectinload(VendorPayment.allocations))
        .order_by(VendorPayment.payment_date.desc(), VendorPayment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_payment(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> VendorPayment | None:
    return await _get_payment(session, tenant_id, payment_id, include_allocations=True)


async def create_payment(session: AsyncSession, tenant_id: UUID, payload: Any) -> VendorPayment:
    data = _to_dict(payload)
    raw_payment_no = data.get("payment_no")
    payment_no = _normalize_payment_no(raw_payment_no) if raw_payment_no else None
    vendor_id = data.get("vendor_id")
    if not vendor_id:
        raise AppException(code="vendor_id_required", message="Vendor is required", http_status=422)
    await _get_vendor(session, tenant_id, vendor_id)
    payment_date = data.get("payment_date")
    if not payment_date:
        raise AppException(code="payment_date_required", message="Payment date is required", http_status=422)
    amount_total = _quantize(data.get("amount_total"))
    if amount_total <= 0:
        raise AppException(
            code="vendor_payment_total_invalid",
            message="Payment total must be greater than zero",
            http_status=422,
        )
    cash_account_id = data.get("cash_account_id")
    if not cash_account_id:
        raise AppException(
            code="vendor_payment_cash_required",
            message="Cash account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, cash_account_id)

    if payment_no:
        existing = await session.execute(
            select(VendorPayment.id).where(
                VendorPayment.tenant_id == tenant_id,
                VendorPayment.payment_no == payment_no,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="vendor_payment_no_exists",
                message="Payment number already exists",
                http_status=409,
            )

    payment = VendorPayment(
        tenant_id=tenant_id,
        vendor_id=vendor_id,
        payment_no=payment_no,
        payment_date=payment_date,
        currency_code=data.get("currency_code"),
        amount_total=amount_total,
        memo=data.get("memo"),
        cash_account_id=cash_account_id,
        status=VendorPaymentStatus.DRAFT,
    )

    async with _transaction_scope(session):
        session.add(payment)
        await session.flush()
    await session.refresh(payment)
    return payment


async def update_payment(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    payload: Any,
) -> VendorPayment | None:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        return None
    if payment.status != VendorPaymentStatus.DRAFT:
        raise AppException(
            code="vendor_payment_not_editable",
            message="Only draft payments can be edited",
            http_status=409,
        )

    data = _to_dict(payload, exclude_unset=True)
    if "payment_no" in data:
        if data["payment_no"] is None:
            payment.payment_no = None
        else:
            payment_no = _normalize_payment_no(data["payment_no"])
            existing = await session.execute(
                select(VendorPayment.id).where(
                    VendorPayment.tenant_id == tenant_id,
                    VendorPayment.payment_no == payment_no,
                    VendorPayment.id != payment_id,
                )
            )
            if existing.scalar_one_or_none():
                raise AppException(
                    code="vendor_payment_no_exists",
                    message="Payment number already exists",
                    http_status=409,
                )
            payment.payment_no = payment_no
    if "payment_date" in data and data["payment_date"] is not None:
        payment.payment_date = data["payment_date"]
    if "currency_code" in data:
        payment.currency_code = data.get("currency_code")
    if "memo" in data:
        payment.memo = data.get("memo")
    if "vendor_id" in data and data["vendor_id"] is not None:
        await _get_vendor(session, tenant_id, data["vendor_id"])
        payment.vendor_id = data["vendor_id"]
    if "cash_account_id" in data and data["cash_account_id"] is not None:
        await _get_account(session, tenant_id, data["cash_account_id"])
        payment.cash_account_id = data["cash_account_id"]
    if "amount_total" in data and data["amount_total"] is not None:
        amount_total = _quantize(data["amount_total"])
        if amount_total <= 0:
            raise AppException(
                code="vendor_payment_total_invalid",
                message="Payment total must be greater than zero",
                http_status=422,
            )
        allocated = await _sum_payment_allocations(session, tenant_id, payment_id)
        if allocated > amount_total:
            raise AppException(
                code="vendor_payment_allocation_exceeds_total",
                message="Allocations exceed payment total",
                http_status=409,
            )
        payment.amount_total = amount_total

    await session.commit()
    await session.refresh(payment)
    return payment


async def list_payment_allocations(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
) -> list[VendorPaymentAllocation]:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)
    result = await session.execute(
        select(VendorPaymentAllocation)
        .where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.payment_id == payment_id,
        )
        .order_by(VendorPaymentAllocation.created_at.asc())
    )
    return list(result.scalars().all())


async def _validate_allocation_target(
    session: AsyncSession,
    tenant_id: UUID,
    payment: VendorPayment,
    bill_id: UUID,
    amount: Decimal,
) -> None:
    bill = await _get_bill(session, tenant_id, bill_id)
    if not bill:
        raise AppException(
            code="purchase_bill_not_found",
            message="Purchase bill not found",
            http_status=404,
        )
    if bill.status == PurchaseInvoiceStatus.REVERSED:
        raise AppException(
            code="purchase_bill_reversed",
            message="Cannot allocate to reversed purchase bill",
            http_status=409,
        )
    if bill.status != PurchaseInvoiceStatus.POSTED:
        raise AppException(
            code="purchase_bill_not_posted",
            message="Purchase bill must be posted before allocation",
            http_status=409,
        )
    if bill.vendor_id != payment.vendor_id:
        raise AppException(
            code="vendor_payment_allocation_invalid",
            message="Allocation must reference a bill for the same vendor",
            http_status=409,
        )
    bill_total = _bill_total(bill)
    allocated = await _sum_posted_bill_allocations(session, tenant_id, bill_id)
    if allocated + amount > bill_total:
        raise AppException(
            code="vendor_payment_allocation_exceeds_bill",
            message="Allocation exceeds bill remaining balance",
            http_status=409,
        )


async def add_payment_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    payload: Any,
) -> VendorPaymentAllocation:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)
    if payment.status != VendorPaymentStatus.DRAFT:
        raise AppException(
            code="vendor_payment_not_editable",
            message="Only draft payments can be edited",
            http_status=409,
        )

    data = _to_dict(payload)
    bill_id = data.get("purchase_bill_id")
    if not bill_id:
        raise AppException(
            code="vendor_payment_allocation_invalid",
            message="Purchase bill is required",
            http_status=422,
        )
    amount = _quantize(data.get("amount"))
    if amount <= 0:
        raise AppException(
            code="vendor_payment_allocation_invalid",
            message="Allocation amount must be greater than zero",
            http_status=422,
        )

    existing = await session.execute(
        select(VendorPaymentAllocation.id).where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.payment_id == payment_id,
            VendorPaymentAllocation.purchase_bill_id == bill_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="vendor_payment_allocation_exists",
            message="Allocation already exists for this bill",
            http_status=409,
        )

    allocated = await _sum_payment_allocations(session, tenant_id, payment_id)
    if allocated + amount > _quantize(payment.amount_total):
        raise AppException(
            code="vendor_payment_allocation_exceeds_total",
            message="Allocations exceed payment total",
            http_status=409,
        )

    await _validate_allocation_target(session, tenant_id, payment, bill_id, amount)

    allocation = VendorPaymentAllocation(
        tenant_id=tenant_id,
        payment_id=payment_id,
        purchase_bill_id=bill_id,
        amount=amount,
    )
    session.add(allocation)
    await session.commit()
    await session.refresh(allocation)
    return allocation


async def update_payment_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    allocation_id: UUID,
    payload: Any,
) -> VendorPaymentAllocation:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)
    if payment.status != VendorPaymentStatus.DRAFT:
        raise AppException(
            code="vendor_payment_not_editable",
            message="Only draft payments can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(VendorPaymentAllocation).where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.payment_id == payment_id,
            VendorPaymentAllocation.id == allocation_id,
        )
    )
    allocation = result.scalar_one_or_none()
    if not allocation:
        raise AppException(
            code="vendor_payment_allocation_not_found",
            message="Payment allocation not found",
            http_status=404,
        )

    data = _to_dict(payload, exclude_unset=True)
    bill_id = data.get("purchase_bill_id", allocation.purchase_bill_id)
    amount = _quantize(data.get("amount", allocation.amount))
    if amount <= 0:
        raise AppException(
            code="vendor_payment_allocation_invalid",
            message="Allocation amount must be greater than zero",
            http_status=422,
        )

    if bill_id != allocation.purchase_bill_id:
        existing = await session.execute(
            select(VendorPaymentAllocation.id).where(
                VendorPaymentAllocation.tenant_id == tenant_id,
                VendorPaymentAllocation.payment_id == payment_id,
                VendorPaymentAllocation.purchase_bill_id == bill_id,
                VendorPaymentAllocation.id != allocation_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="vendor_payment_allocation_exists",
                message="Allocation already exists for this bill",
                http_status=409,
            )

    allocated = await _sum_payment_allocations(session, tenant_id, payment_id)
    allocated = allocated - _quantize(allocation.amount) + amount
    if allocated > _quantize(payment.amount_total):
        raise AppException(
            code="vendor_payment_allocation_exceeds_total",
            message="Allocations exceed payment total",
            http_status=409,
        )

    await _validate_allocation_target(session, tenant_id, payment, bill_id, amount)

    allocation.purchase_bill_id = bill_id
    allocation.amount = amount

    await session.commit()
    await session.refresh(allocation)
    return allocation


async def delete_payment_allocation(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    allocation_id: UUID,
) -> bool:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)
    if payment.status != VendorPaymentStatus.DRAFT:
        raise AppException(
            code="vendor_payment_not_editable",
            message="Only draft payments can be edited",
            http_status=409,
        )

    result = await session.execute(
        select(VendorPaymentAllocation).where(
            VendorPaymentAllocation.tenant_id == tenant_id,
            VendorPaymentAllocation.payment_id == payment_id,
            VendorPaymentAllocation.id == allocation_id,
        )
    )
    allocation = result.scalar_one_or_none()
    if not allocation:
        return False
    await session.delete(allocation)
    await session.commit()
    return True


async def post_payment(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> VendorPayment:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=True)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)

    if payment.status == VendorPaymentStatus.POSTED:
        raise AppException(
            code="vendor_payment_already_posted",
            message="Payment has already been posted",
            http_status=409,
        )
    if payment.status == VendorPaymentStatus.REVERSED:
        raise AppException(
            code="vendor_payment_not_draft",
            message="Only draft payments can be posted",
            http_status=409,
        )
    if payment.posting_journal_entry_id:
        raise AppException(
            code="vendor_payment_already_posted",
            message="Payment has already been posted",
            http_status=409,
        )

    amount_total = _quantize(payment.amount_total)
    if amount_total <= 0:
        raise AppException(
            code="vendor_payment_total_invalid",
            message="Payment total must be greater than zero",
            http_status=422,
        )
    if not payment.cash_account_id:
        raise AppException(
            code="vendor_payment_cash_required",
            message="Cash account is required",
            http_status=422,
        )
    await _get_account(session, tenant_id, payment.cash_account_id)

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=payment.payment_date)

    vendor = await _get_vendor(session, tenant_id, payment.vendor_id)
    if vendor.status == VendorStatus.INACTIVE:
        raise AppException(
            code="vendor_inactive",
            message="Vendor is inactive",
            http_status=409,
        )

    existing_entry = await _find_payment_entry(session, tenant_id, payment_id)
    if existing_entry and existing_entry.status == STATUS_POSTED:
        payment.status = VendorPaymentStatus.POSTED
        payment.posted_at = existing_entry.posted_at or existing_entry.posting_date or datetime.now(UTC)
        payment.posting_journal_entry_id = existing_entry.id
        await session.commit()
        await session.refresh(payment)
        raise AppException(
            code="vendor_payment_already_posted",
            message="Payment has already been posted",
            http_status=409,
        )

    applied_total = Decimal("0.00")
    for allocation in payment.allocations:
        applied_total += _quantize(allocation.amount)
    applied_total = _quantize(applied_total)
    if applied_total > amount_total:
        raise AppException(
            code="vendor_payment_allocation_exceeds_total",
            message="Allocations exceed payment total",
            http_status=409,
        )

    for allocation in payment.allocations:
        await _validate_allocation_target(
            session,
            tenant_id,
            payment,
            allocation.purchase_bill_id,
            _quantize(allocation.amount),
        )

    unapplied_amount = _quantize(amount_total - applied_total)

    ap_account_id = await _get_ap_control_account_id(session, tenant_id)
    prepay_account_id = await _get_vendor_prepay_account_id(session, tenant_id)
    currency = await _resolve_currency(session, tenant_id, payment.currency_code)

    for attempt in range(5):
        try:
            async with _transaction_scope(session):
                locked_result = await session.execute(
                    select(VendorPayment)
                    .where(VendorPayment.id == payment_id, VendorPayment.tenant_id == tenant_id)
                    .options(lazyload(VendorPayment.vendor))
                    .with_for_update()
                )
                locked_payment = locked_result.scalar_one_or_none()
                if not locked_payment:
                    raise AppException(
                        code="vendor_payment_not_found",
                        message="Payment not found",
                        http_status=404,
                    )
                if not locked_payment.payment_no:
                    locked_payment.payment_no = await _ensure_payment_no(
                        session, tenant_id, locked_payment.payment_no
                    )
                payment_no = locked_payment.payment_no

                lines: list[JournalLineCreate] = [
                    JournalLineCreate(
                        account_id=locked_payment.cash_account_id,
                        debit_amount=Decimal("0.00"),
                        credit_amount=amount_total,
                        line_currency=currency,
                        memo=f"Payment {payment_no}",
                    )
                ]
                if applied_total > 0:
                    lines.append(
                        JournalLineCreate(
                            account_id=ap_account_id,
                            debit_amount=applied_total,
                            credit_amount=Decimal("0.00"),
                            line_currency=currency,
                            memo=f"Payment {payment_no}",
                        )
                    )
                if unapplied_amount > 0:
                    lines.append(
                        JournalLineCreate(
                            account_id=prepay_account_id,
                            debit_amount=unapplied_amount,
                            credit_amount=Decimal("0.00"),
                            line_currency=currency,
                            memo=f"Payment {payment_no}",
                        )
                    )

                ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
                entry = await ledger.create_manual_entry(
                    entry_date=locked_payment.payment_date,
                    base_currency=currency,
                    memo=f"Payment {payment_no}",
                    source_type="vendor_payment",
                    source_id=payment_id,
                    lines=lines,
                    commit=False,
                )
                posted_entry = await ledger.post_entry(entry.id, commit=False)
                locked_payment.status = VendorPaymentStatus.POSTED
                locked_payment.posted_at = posted_entry.posted_at or datetime.now(UTC)
                locked_payment.posting_journal_entry_id = posted_entry.id
                payment = locked_payment
            break
        except IntegrityError as exc:
            await session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_vendor_payments_tenant_payment_no" in message:
                payment = await _get_payment(session, tenant_id, payment_id, include_allocations=True)
                if not payment:
                    raise
                if payment.payment_no:
                    raise AppException(
                        code="vendor_payment_no_exists",
                        message="Payment number already exists",
                        http_status=409,
                    ) from exc
                continue
            raise

    await session.refresh(payment)
    return payment


async def reverse_payment(
    session: AsyncSession,
    tenant_id: UUID,
    payment_id: UUID,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> VendorPayment:
    payment = await _get_payment(session, tenant_id, payment_id, include_allocations=False)
    if not payment:
        raise AppException(code="vendor_payment_not_found", message="Payment not found", http_status=404)

    if payment.status == VendorPaymentStatus.REVERSED:
        raise AppException(
            code="vendor_payment_already_reversed",
            message="Payment has already been reversed",
            http_status=409,
        )
    if payment.status != VendorPaymentStatus.POSTED:
        raise AppException(
            code="vendor_payment_not_posted",
            message="Only posted payments can be reversed",
            http_status=409,
        )
    if payment.reversal_journal_entry_id:
        raise AppException(
            code="vendor_payment_already_reversed",
            message="Payment has already been reversed",
            http_status=409,
        )

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=payment.payment_date)

    entry = await _find_payment_entry(session, tenant_id, payment_id)
    if not entry:
        raise AppException(
            code="vendor_payment_missing_journal_entry",
            message="Posted payment is missing journal entry",
            http_status=409,
        )
    entry_id = entry.id
    if entry.status == STATUS_REVERSED or entry.is_reversed:
        reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
        payment.status = VendorPaymentStatus.REVERSED
        payment.reversed_at = (
            reversal_entry.posted_at or reversal_entry.posting_date if reversal_entry else datetime.now(UTC)
        )
        if reversal_entry:
            payment.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(payment)
        raise AppException(
            code="vendor_payment_already_reversed",
            message="Payment has already been reversed",
            http_status=409,
        )

    reversal_entry = await _find_reversal_entry(session, tenant_id, entry_id)
    if reversal_entry:
        payment.status = VendorPaymentStatus.REVERSED
        payment.reversed_at = reversal_entry.posted_at or reversal_entry.posting_date or datetime.now(UTC)
        payment.reversal_journal_entry_id = reversal_entry.id
        await session.commit()
        await session.refresh(payment)
        raise AppException(
            code="vendor_payment_already_reversed",
            message="Payment has already been reversed",
            http_status=409,
        )

    async with _transaction_scope(session):
        locked_result = await session.execute(
            select(VendorPayment)
            .where(VendorPayment.id == payment_id, VendorPayment.tenant_id == tenant_id)
            .options(lazyload(VendorPayment.vendor))
            .with_for_update()
        )
        locked_payment = locked_result.scalar_one_or_none()
        if not locked_payment:
            raise AppException(
                code="vendor_payment_not_found",
                message="Payment not found",
                http_status=404,
            )
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        reversed_entry = await ledger.reverse_entry(entry_id, reason=reason.strip(), commit=False)
        locked_payment.status = VendorPaymentStatus.REVERSED
        locked_payment.reversed_at = reversed_entry.posted_at or datetime.now(UTC)
        locked_payment.reversal_journal_entry_id = reversed_entry.id
        payment = locked_payment

    await session.refresh(payment)
    return payment


__all__ = [
    "list_payments",
    "get_payment",
    "create_payment",
    "update_payment",
    "list_payment_allocations",
    "add_payment_allocation",
    "update_payment_allocation",
    "delete_payment_allocation",
    "post_payment",
    "reverse_payment",
]
