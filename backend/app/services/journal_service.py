from __future__ import annotations

import uuid
from datetime import UTC, datetime, date
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.accounting.dto import LedgerLineInput, RecordFinancialTransactionInput, TreasuryMovementInput
from app.accounting.use_cases.record_financial_transaction import record_financial_transaction
from app.accounting.repositories.period_lock_repo import PeriodLockRepository
from app.core.exceptions import AppException
from app.core.permissions import PermissionCode
from app.models.journal_entry import JournalEntry
from app.models.treasury_transaction import TreasuryTransaction
from app.services import audit_log_service
from app.services.permission_service import require_permission


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _entry_is_posted(entry: JournalEntry) -> bool:
    return bool(entry.is_posted) or str(entry.status or "").lower() == "posted"


async def _require_permission(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    permission_code: str,
) -> None:
    await require_permission(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        permission_code=permission_code,
    )


async def _has_reversal_entry(session: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
    stmt = select(JournalEntry.id).where(
        JournalEntry.tenant_id == tenant_id,
        or_(
            JournalEntry.reversed_of_id == entry_id,
            JournalEntry.reversal_of_entry_id == entry_id,
        ),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _load_entry(session: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID, *, include_lines: bool = False) -> JournalEntry | None:
    stmt = select(JournalEntry).where(
        JournalEntry.id == entry_id,
        JournalEntry.tenant_id == tenant_id,
    )
    if include_lines:
        stmt = stmt.options(selectinload(JournalEntry.lines))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_journal_entries(session: AsyncSession, tenant_id: uuid.UUID) -> Sequence[JournalEntry]:
    result = await session.execute(select(JournalEntry).where(JournalEntry.tenant_id == tenant_id))
    return result.scalars().all()


async def get_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> JournalEntry | None:
    return await _load_entry(session, tenant_id, entry_id, include_lines=True)


async def create_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payload: Any,
    *,
    actor_id: uuid.UUID | None = None,
) -> JournalEntry:
    await _require_permission(session, tenant_id, actor_id, PermissionCode.JOURNAL_CREATE.value)
    data = _to_dict(payload)
    lines_data = data.pop("lines", None)
    if not lines_data:
        raise ValueError("Journal entry requires at least one line")

    reference_type = data.get("source_module") or data.get("reference") or "manual_journal"
    reference_id = data.get("source_id") or uuid.uuid4()

    result = await record_financial_transaction(
        session,
        RecordFinancialTransactionInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            date=data["date"],
            description=data.get("description"),
            reference_type=str(reference_type),
            reference_id=reference_id,
            lines=[
                {
                    "account_id": line["account_id"],
                    "debit": Decimal(str(line.get("debit") or 0)),
                    "credit": Decimal(str(line.get("credit") or 0)),
                    "entity_type": line.get("entity_type"),
                    "entity_id": line.get("entity_id"),
                    "reference_type": line.get("reference_type") or str(reference_type),
                    "reference_id": line.get("reference_id") or reference_id,
                    "description": line.get("line_description"),
                }
                for line in lines_data
            ],
            treasury_movement=None,
        ),
        commit=True,
    )

    entry = await get_journal_entry(session, tenant_id, result.journal_entry_id)
    if entry is None:
        raise AppException(
            code="journal_entry_not_found",
            message="Journal entry created but could not be loaded",
            http_status=500,
        )
    return entry


async def update_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: Any,
    *,
    actor_id: uuid.UUID | None = None,
) -> JournalEntry | None:
    await _require_permission(session, tenant_id, actor_id, PermissionCode.JOURNAL_UPDATE.value)
    _ = payload
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise AppException(
            code="journal_entry_not_found",
            message="Journal entry not found",
            http_status=404,
        )
    if _entry_is_posted(entry):
        raise AppException(
            code="journal_posted_immutable",
            message="Posted journal entries are immutable",
            http_status=409,
        )
    raise AppException(
        code="journal_updates_disabled",
        message="Updating journal entries is disabled; create a new correction entry instead",
        http_status=405,
    )


async def create_journal_entry_with_lines(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    date: date,
    description: str | None,
    lines: list[dict[str, Any]],
    reference: str | None = None,
    *,
    currency_code: str | None = None,
    fx_rate: float | Decimal | None = None,
    source_module: str | None = None,
    source_id: uuid.UUID | None = None,
    is_posted: bool = True,
    reversed_of_id: uuid.UUID | None = None,
) -> JournalEntry:
    _ = (
        session,
        tenant_id,
        date,
        description,
        lines,
        reference,
        currency_code,
        fx_rate,
        source_module,
        source_id,
        is_posted,
        reversed_of_id,
    )
    raise AppException(
        code="journal_writes_must_use_engine",
        message="Direct journal writes are disabled; use record_financial_transaction",
        http_status=405,
    )


async def create_reversing_entry(*args, **kwargs):
    """Backward-compatibility shim; prefer the fully typed create_reversing_entry_impl."""
    return await create_reversing_entry_impl(*args, **kwargs)


async def create_reversing_entry_impl(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    original_journal_entry_id: uuid.UUID,
    reversal_date: date,
) -> JournalEntry:
    _ = session, tenant_id, original_journal_entry_id, reversal_date
    raise AppException(
        code="journal_writes_must_use_engine",
        message="Direct journal writes are disabled; use record_financial_transaction",
        http_status=405,
    )


async def delete_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> bool:
    await _require_permission(session, tenant_id, actor_id, PermissionCode.JOURNAL_DELETE.value)
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise AppException(
            code="journal_entry_not_found",
            message="Journal entry not found",
            http_status=404,
        )
    if _entry_is_posted(entry):
        raise AppException(
            code="journal_posted_immutable",
            message="Posted journal entries are immutable",
            http_status=409,
        )
    raise AppException(code="deletes_disabled", message="Deleting journal entries is disabled", http_status=405)


async def _ensure_period_open(session: AsyncSession, tenant_id: uuid.UUID, entry_date: date) -> None:
    period_lock_repo = PeriodLockRepository(session=session)
    if await period_lock_repo.is_locked(tenant_id=tenant_id, entry_date=entry_date):
        raise AppException(
            code="accounting_period_locked",
            message="Accounting period is locked for the provided date",
            http_status=409,
        )


async def reverse_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> JournalEntry:
    await _require_permission(session, tenant_id, actor_id, PermissionCode.JOURNAL_REVERSE.value)
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise AppException(code="journal_entry_not_found", message="Journal entry not found", http_status=404)
    if entry.is_voided:
        raise AppException(code="journal_entry_voided", message="Cannot reverse a voided entry", http_status=409)
    if not entry.is_posted:
        raise AppException(
            code="journal_reverse_disallowed",
            message="Only posted entries can be reversed",
            http_status=409,
        )
    if entry.is_reversed:
        raise AppException(
            code="journal_already_reversed",
            message="Journal entry has already been reversed",
            http_status=409,
        )
    if await _has_reversal_entry(session, tenant_id, entry.id):
        raise AppException(
            code="journal_already_reversed",
            message="Journal entry has already been reversed",
            http_status=409,
        )
    await _ensure_period_open(session, tenant_id, entry.date)
    reversal_date = datetime.now(UTC).date()
    await _ensure_period_open(session, tenant_id, reversal_date)

    lines = [
        LedgerLineInput(
            account_id=line.account_id,
            debit=line.credit,
            credit=line.debit,
            entity_type=line.entity_type,
            entity_id=line.entity_id,
            reference_type=line.reference_type or "journal_reversal",
            reference_id=line.reference_id or entry.id,
            description=f"Reversal of {line.line_description or entry.description or ''}".strip(),
            currency_amount=line.currency_amount,
        )
        for line in entry.lines
    ]

    treasury_movement = None
    original_treasury_tx = None
    if entry.treasury_transaction_id:
        tx_result = await session.execute(
            select(TreasuryTransaction).where(
                TreasuryTransaction.id == entry.treasury_transaction_id,
                TreasuryTransaction.tenant_id == tenant_id,
            )
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            direction = "out" if tx.direction == "in" else "in"
            party_type = None
            party_id = None
            if tx.customer_id:
                party_type, party_id = "client", tx.customer_id
            elif tx.supplier_id:
                party_type, party_id = "supplier", tx.supplier_id
            elif tx.employee_id:
                party_type, party_id = "worker", tx.employee_id
            treasury_movement = TreasuryMovementInput(
                treasury_id=tx.treasury_id,
                amount=Decimal(str(tx.amount)),
                direction=direction,
                reference_type="journal_reversal",
                reference_id=entry.id,
                movement_type=tx.movement_type,
                party_type=party_type,
                party_id=party_id,
                reversed_of_id=tx.id,
            )
            original_treasury_tx = tx

    metadata = {
        "reversed_of_id": entry.id,
        "is_reversed": True,
        "adjustment_reason": reason,
    }

    try:
        result = await record_financial_transaction(
            session,
            RecordFinancialTransactionInput(
                tenant_id=tenant_id,
                actor_id=actor_id,
                date=reversal_date,
                description=reason or f"Reversal of {entry.id}",
                reference_type=entry.source_module or entry.reference or "journal_reversal",
                reference_id=entry.id,
                lines=lines,
                treasury_movement=treasury_movement,
                entry_metadata=metadata,
            ),
            commit=True,
        )
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "ux_journal_entries_reversed_of_id" in message or "reversed_of_id" in message:
            raise AppException(
                code="journal_already_reversed",
                message="Journal entry has already been reversed",
                http_status=409,
            ) from exc
        raise

    reversed_entry = await get_journal_entry(session, tenant_id, result.journal_entry_id)
    if reversed_entry is None:
        raise AppException(
            code="journal_entry_not_found",
            message="Reversal created but could not be loaded",
            http_status=500,
        )

    entry.is_reversed = True
    if original_treasury_tx:
        original_treasury_tx.is_reversed = True
    await session.commit()

    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "journal_entries",
        str(entry.id),
        "journal_entry_reverse",
        user_id=actor_id,
        new_data={
            "reversal_id": str(reversed_entry.id),
            "reason": reason,
        },
    )
    return reversed_entry


async def void_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> JournalEntry:
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise AppException(code="journal_entry_not_found", message="Journal entry not found", http_status=404)
    if entry.is_voided:
        raise AppException(code="journal_entry_voided", message="Journal entry already voided", http_status=409)
    if entry.is_posted:
        raise AppException(
            code="journal_posted_immutable",
            message="Posted journal entries are immutable",
            http_status=409,
        )

    await _ensure_period_open(session, tenant_id, entry.date)
    entry.is_voided = True
    entry.voided_at = datetime.now(UTC)
    entry.voided_by_user_id = actor_id
    if reason:
        entry.voided_reason = reason
    if entry.treasury_transaction_id:
        tx_result = await session.execute(
            select(TreasuryTransaction).where(
                TreasuryTransaction.id == entry.treasury_transaction_id,
                TreasuryTransaction.tenant_id == tenant_id,
            )
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            tx.is_voided = True
            tx.voided_at = entry.voided_at
            tx.voided_by_user_id = actor_id
            if reason:
                tx.voided_reason = reason
    await session.commit()
    await session.refresh(entry)

    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "journal_entries",
        str(entry.id),
        "journal_entry_void",
        user_id=actor_id,
        new_data={"reason": reason},
    )
    return entry


async def adjust_journal_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
    reason: str | None = None,
    lines: Sequence[dict[str, Any]],
    idempotency_key: str,
) -> JournalEntry:
    if not idempotency_key:
        raise AppException(code="missing_idempotency_key", message="Idempotency-Key header required", http_status=400)
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise AppException(code="journal_entry_not_found", message="Journal entry not found", http_status=404)
    if entry.is_voided:
        raise AppException(code="journal_entry_voided", message="Cannot adjust a voided entry", http_status=409)
    if _entry_is_posted(entry):
        raise AppException(
            code="journal_posted_immutable",
            message="Posted journal entries can only be reversed",
            http_status=409,
        )
    await _ensure_period_open(session, tenant_id, datetime.now(UTC).date())

    existing = await session.execute(
        select(JournalEntry).where(
            JournalEntry.adjusted_of_id == entry.id,
            JournalEntry.idempotency_key == idempotency_key,
        )
    )
    existing_entry = existing.scalar_one_or_none()
    if existing_entry:
        return existing_entry

    parsed_lines = [
        LedgerLineInput(
            account_id=Line["account_id"],
            debit=Line.get("debit") or Decimal("0"),
            credit=Line.get("credit") or Decimal("0"),
            entity_type=Line.get("entity_type"),
            entity_id=Line.get("entity_id"),
            reference_type=Line.get("reference_type") or "journal_adjustment",
            reference_id=Line.get("reference_id") or entry.id,
            description=Line.get("line_description"),
            currency_amount=Line.get("currency_amount"),
        )
        for Line in lines
    ]

    metadata = {
        "adjusted_of_id": entry.id,
        "idempotency_key": idempotency_key,
        "adjustment_reason": reason,
    }

    result = await record_financial_transaction(
        session,
        RecordFinancialTransactionInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            date=datetime.now(UTC).date(),
            description=reason or f"Adjustment of {entry.id}",
            reference_type=entry.source_module or entry.reference or "journal_adjustment",
            reference_id=entry.id,
            lines=parsed_lines,
            entry_metadata=metadata,
        ),
        commit=True,
    )

    adjustment_entry = await get_journal_entry(session, tenant_id, result.journal_entry_id)
    if adjustment_entry is None:
        raise AppException(
            code="journal_entry_not_found",
            message="Adjustment created but could not be loaded",
            http_status=500,
        )

    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "journal_entries",
        str(entry.id),
        "journal_entry_adjust",
        user_id=actor_id,
        new_data={"adjustment_id": str(adjustment_entry.id), "reason": reason},
    )
    return adjustment_entry


__all__ = [
    "list_journal_entries",
    "get_journal_entry",
    "create_journal_entry",
    "create_journal_entry_with_lines",
    "update_journal_entry",
    "delete_journal_entry",
    "create_reversing_entry",
    "create_reversing_entry_impl",
    "reverse_journal_entry",
    "void_journal_entry",
    "adjust_journal_entry",
]
