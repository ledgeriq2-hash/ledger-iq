from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.account import Account
from app.models.treasury_cash_account import TreasuryCashAccount
from app.models.treasury_cash_transaction import (
    CashTransactionStatus,
    CashTransactionType,
    TreasuryCashTransaction,
)
from app.schemas.journals import JournalLineCreate
from app.services.ledger_service import DEFAULT_BASE_CURRENCY, LedgerService
from app.services.period_guard import PeriodGuard
from app.services import settings_service
from app.treasury.repositories.cash_account_repo import CashAccountRepository
from app.treasury.repositories.cash_transaction_repo import CashTransactionRepository


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _quantize(amount: Decimal | str | int | float) -> Decimal:
    return Decimal(str(amount)).quantize(Decimal("0.01"))


@asynccontextmanager
async def _transaction_scope(session: AsyncSession):
    if session.in_transaction():
        await session.rollback()
    async with session.begin():
        yield


async def _resolve_currency(session: AsyncSession, tenant_id: UUID) -> str:
    settings = await settings_service.get_settings(session, tenant_id)
    currency = (settings.currency or "").strip().upper()
    return currency or DEFAULT_BASE_CURRENCY


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


async def _get_cash_account(
    session: AsyncSession, tenant_id: UUID, cash_account_id: UUID
) -> TreasuryCashAccount:
    repo = CashAccountRepository(session=session)
    cash_account = await repo.get(tenant_id=tenant_id, cash_account_id=cash_account_id)
    if not cash_account:
        raise AppException(code="cash_account_not_found", message="Cash account not found", http_status=404)
    await _get_account(session, tenant_id, cash_account.account_id)
    return cash_account


def _normalize_transaction_type(value: Any) -> CashTransactionType:
    if isinstance(value, CashTransactionType):
        return value
    try:
        return CashTransactionType(str(value).strip().upper())
    except ValueError as exc:
        raise AppException(
            code="cash_transaction_type_invalid",
            message="Invalid cash transaction type",
            http_status=422,
        ) from exc


async def list_cash_accounts(session: AsyncSession, tenant_id: UUID) -> Sequence[TreasuryCashAccount]:
    repo = CashAccountRepository(session=session)
    return await repo.list(tenant_id=tenant_id)


async def create_cash_account(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> TreasuryCashAccount:
    _ = actor_id
    data = _to_dict(payload)
    name = (data.get("name") or "").strip()
    if not name:
        raise AppException(code="cash_account_name_required", message="Cash account name is required", http_status=422)

    account_id = data.get("account_id")
    if not account_id:
        raise AppException(code="ledger_account_required", message="Ledger account is required", http_status=422)

    await _get_account(session, tenant_id, account_id)

    repo = CashAccountRepository(session=session)
    account = await repo.create(
        tenant_id=tenant_id,
        name=name,
        account_id=account_id,
        description=(data.get("description") or None),
    )
    await session.commit()
    await session.refresh(account)
    return account


async def list_cash_transactions(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    transaction_type: CashTransactionType | None = None,
    status: CashTransactionStatus | None = None,
    cash_account_id: UUID | None = None,
    counterparty_account_id: UUID | None = None,
    from_cash_account_id: UUID | None = None,
    to_cash_account_id: UUID | None = None,
    posting_date_start: date | None = None,
    posting_date_end: date | None = None,
) -> Sequence[TreasuryCashTransaction]:
    repo = CashTransactionRepository(session=session)
    return await repo.list(
        tenant_id=tenant_id,
        transaction_type=transaction_type,
        status=status,
        cash_account_id=cash_account_id,
        counterparty_account_id=counterparty_account_id,
        from_cash_account_id=from_cash_account_id,
        to_cash_account_id=to_cash_account_id,
        posting_date_start=posting_date_start,
        posting_date_end=posting_date_end,
    )


async def create_cash_transaction(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> TreasuryCashTransaction:
    _ = actor_id
    data = _to_dict(payload)
    if data.get("amount") is None:
        raise AppException(code="cash_transaction_amount_required", message="Amount is required", http_status=422)

    tx_type = _normalize_transaction_type(data.get("transaction_type"))
    amount = _quantize(data.get("amount"))
    if amount <= 0:
        raise AppException(
            code="cash_transaction_amount_invalid",
            message="Amount must be greater than zero",
            http_status=422,
        )

    posting_date = data.get("posting_date") or date.today()

    cash_account_id = data.get("cash_account_id")
    counterparty_account_id = data.get("counterparty_account_id")
    from_cash_account_id = data.get("from_cash_account_id")
    to_cash_account_id = data.get("to_cash_account_id")

    if tx_type in {CashTransactionType.RECEIPT, CashTransactionType.PAYMENT}:
        if not cash_account_id or not counterparty_account_id:
            raise AppException(
                code="cash_transaction_accounts_required",
                message="Cash account and counterparty account are required",
                http_status=422,
            )
        if from_cash_account_id or to_cash_account_id:
            raise AppException(
                code="cash_transaction_transfer_fields_invalid",
                message="Transfer account fields are not allowed for this transaction type",
                http_status=422,
            )
        await _get_cash_account(session, tenant_id, cash_account_id)
        await _get_account(session, tenant_id, counterparty_account_id)
    elif tx_type == CashTransactionType.TRANSFER:
        if not from_cash_account_id or not to_cash_account_id:
            raise AppException(
                code="cash_transaction_accounts_required",
                message="From and to cash accounts are required",
                http_status=422,
            )
        if from_cash_account_id == to_cash_account_id:
            raise AppException(
                code="cash_transaction_transfer_same_account",
                message="Transfer cash accounts must be different",
                http_status=422,
            )
        if cash_account_id or counterparty_account_id:
            raise AppException(
                code="cash_transaction_receipt_fields_invalid",
                message="Cash/counterparty fields are not allowed for transfers",
                http_status=422,
            )
        await _get_cash_account(session, tenant_id, from_cash_account_id)
        await _get_cash_account(session, tenant_id, to_cash_account_id)
    else:
        raise AppException(
            code="cash_transaction_type_invalid",
            message="Invalid cash transaction type",
            http_status=422,
        )

    repo = CashTransactionRepository(session=session)
    tx = await repo.create_draft(
        tenant_id=tenant_id,
        transaction_type=tx_type,
        amount=amount,
        posting_date=posting_date,
        description=(data.get("description") or None),
        cash_account_id=cash_account_id,
        counterparty_account_id=counterparty_account_id,
        from_cash_account_id=from_cash_account_id,
        to_cash_account_id=to_cash_account_id,
    )
    await session.commit()
    await session.refresh(tx)
    return tx


async def post_cash_transaction(
    session: AsyncSession,
    tenant_id: UUID,
    transaction_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> TreasuryCashTransaction:
    repo = CashTransactionRepository(session=session)
    tx = await repo.get(tenant_id=tenant_id, transaction_id=transaction_id)
    if not tx:
        raise AppException(code="cash_transaction_not_found", message="Cash transaction not found", http_status=404)

    if tx.status == CashTransactionStatus.POSTED:
        raise AppException(
            code="cash_transaction_already_posted",
            message="Cash transaction has already been posted",
            http_status=409,
        )
    if tx.status == CashTransactionStatus.REVERSED:
        raise AppException(
            code="cash_transaction_already_reversed",
            message="Reversed cash transactions cannot be posted",
            http_status=409,
        )

    if not tx.posting_date:
        raise AppException(
            code="cash_transaction_posting_date_required",
            message="Posting date is required",
            http_status=422,
        )

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=tx.posting_date)

    description = (tx.description or f"Cash transaction {tx.id}").strip()
    amount = _quantize(tx.amount)

    currency = await _resolve_currency(session, tenant_id)
    tx_id = tx.id
    lines: list[JournalLineCreate]
    if tx.transaction_type == CashTransactionType.RECEIPT:
        if not tx.cash_account_id or not tx.counterparty_account_id:
            raise AppException(
                code="cash_transaction_accounts_required",
                message="Cash account and counterparty account are required",
                http_status=422,
            )
        cash_account = await _get_cash_account(session, tenant_id, tx.cash_account_id)
        await _get_account(session, tenant_id, tx.counterparty_account_id)
        lines = [
            JournalLineCreate(
                account_id=cash_account.account_id,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                line_currency=currency,
                memo=description,
            ),
            JournalLineCreate(
                account_id=tx.counterparty_account_id,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                line_currency=currency,
                memo=description,
            ),
        ]
    elif tx.transaction_type == CashTransactionType.PAYMENT:
        if not tx.cash_account_id or not tx.counterparty_account_id:
            raise AppException(
                code="cash_transaction_accounts_required",
                message="Cash account and counterparty account are required",
                http_status=422,
            )
        cash_account = await _get_cash_account(session, tenant_id, tx.cash_account_id)
        await _get_account(session, tenant_id, tx.counterparty_account_id)
        lines = [
            JournalLineCreate(
                account_id=tx.counterparty_account_id,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                line_currency=currency,
                memo=description,
            ),
            JournalLineCreate(
                account_id=cash_account.account_id,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                line_currency=currency,
                memo=description,
            ),
        ]
    elif tx.transaction_type == CashTransactionType.TRANSFER:
        if not tx.from_cash_account_id or not tx.to_cash_account_id:
            raise AppException(
                code="cash_transaction_accounts_required",
                message="From and to cash accounts are required",
                http_status=422,
            )
        if tx.from_cash_account_id == tx.to_cash_account_id:
            raise AppException(
                code="cash_transaction_transfer_same_account",
                message="Transfer cash accounts must be different",
                http_status=422,
            )
        from_cash_account = await _get_cash_account(session, tenant_id, tx.from_cash_account_id)
        to_cash_account = await _get_cash_account(session, tenant_id, tx.to_cash_account_id)
        lines = [
            JournalLineCreate(
                account_id=to_cash_account.account_id,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                line_currency=currency,
                memo=description,
            ),
            JournalLineCreate(
                account_id=from_cash_account.account_id,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                line_currency=currency,
                memo=description,
            ),
        ]
    else:
        raise AppException(
            code="cash_transaction_type_invalid",
            message="Invalid cash transaction type",
            http_status=422,
        )

    async with _transaction_scope(session):
        tx = await repo.get(tenant_id=tenant_id, transaction_id=tx_id)
        if not tx:
            raise AppException(code="cash_transaction_not_found", message="Cash transaction not found", http_status=404)
        ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
        entry = await ledger.create_manual_entry(
            entry_date=tx.posting_date,
            base_currency=currency,
            memo=description,
            source_type="treasury_cash",
            source_id=tx.id,
            lines=lines,
            commit=False,
        )
        posted_entry = await ledger.post_entry(entry.id, commit=False)

        tx.journal_entry_id = posted_entry.id
        tx.status = CashTransactionStatus.POSTED
        tx.posted_at = datetime.now(UTC)

    await session.refresh(tx)
    return tx


async def reverse_cash_transaction(
    session: AsyncSession,
    tenant_id: UUID,
    transaction_id: UUID,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> TreasuryCashTransaction:
    if not reason or not reason.strip():
        raise AppException(
            code="cash_transaction_reverse_reason_required",
            message="Reversal reason is required",
            http_status=422,
        )

    repo = CashTransactionRepository(session=session)
    tx = await repo.get(tenant_id=tenant_id, transaction_id=transaction_id)
    if not tx:
        raise AppException(code="cash_transaction_not_found", message="Cash transaction not found", http_status=404)

    if tx.status == CashTransactionStatus.REVERSED:
        raise AppException(
            code="cash_transaction_already_reversed",
            message="Cash transaction has already been reversed",
            http_status=409,
        )
    if tx.status != CashTransactionStatus.POSTED:
        raise AppException(
            code="cash_transaction_not_posted",
            message="Only posted cash transactions can be reversed",
            http_status=409,
        )
    if not tx.journal_entry_id:
        raise AppException(
            code="cash_transaction_missing_journal_entry",
            message="Posted cash transaction is missing journal entry",
            http_status=409,
        )

    ledger = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    reversal_entry = await ledger.reverse_entry(tx.journal_entry_id, reason=reason.strip())

    tx.status = CashTransactionStatus.REVERSED
    tx.reversal_journal_entry_id = reversal_entry.id
    tx.reversal_reason = reason.strip()
    tx.reversed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(tx)
    return tx


__all__ = [
    "list_cash_accounts",
    "create_cash_account",
    "list_cash_transactions",
    "create_cash_transaction",
    "post_cash_transaction",
    "reverse_cash_transaction",
]
