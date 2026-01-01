from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.dto import RecordFinancialTransactionInput, RecordFinancialTransactionOutput
from app.accounting.repositories.ledger_repo import LedgerRepository
from app.accounting.repositories.period_lock_repo import PeriodLockRepository
from app.core.exceptions import AppException
from app.services.accounting_mapping import ACCOUNT_MAPPING_REQUIREMENTS, validate_tenant_account_mapping
from app.shared.audit import build_audit_log
from app.treasury.repositories.treasury_repo import TreasuryRepository


async def record_financial_transaction(
    session: AsyncSession,
    payload: RecordFinancialTransactionInput,
    *,
    commit: bool = True,
) -> RecordFinancialTransactionOutput:
    period_lock_repo = PeriodLockRepository(session=session)
    if await period_lock_repo.is_locked(tenant_id=payload.tenant_id, entry_date=payload.date):
        raise AppException(
            code="accounting_period_locked",
            message="Accounting period is locked for the provided date",
            http_status=409,
        )

    zero_amount_lines = []
    normalized_lines: list[tuple[int, Decimal, Decimal]] = []
    for index, line in enumerate(payload.lines):
        debit = Decimal(str(line.debit or 0)).quantize(Decimal("0.01"))
        credit = Decimal(str(line.credit or 0)).quantize(Decimal("0.01"))
        if debit == Decimal("0.00") and credit == Decimal("0.00"):
            zero_amount_lines.append(index)
        normalized_lines.append((index, debit, credit))

    if zero_amount_lines:
        raise AppException(
            code="zero_amount_line",
            message="Journal entry lines must have a non-zero debit or credit",
            details={"line_indexes": zero_amount_lines},
            http_status=422,
        )

    debit_total = sum(debit for _, debit, _ in normalized_lines)
    credit_total = sum(credit for _, _, credit in normalized_lines)
    if debit_total != credit_total:
        raise AppException(
            code="journal_not_balanced",
            message="Journal entry is not balanced (debits != credits)",
            details={"debit_total": str(debit_total), "credit_total": str(credit_total)},
            http_status=422,
        )

    currency_code = (payload.currency_code or "").strip().upper() or None
    if payload.fx_rate is not None and currency_code is None:
        raise AppException(
            code="currency_code_required",
            message="currency_code is required when fx_rate is provided",
            http_status=422,
        )
    if currency_code is None:
        if any(line.currency_amount is not None for line in payload.lines):
            raise AppException(
                code="currency_code_required",
                message="currency_code is required when currency_amount is provided",
                http_status=422,
            )
    else:
        missing_currency_amounts = [
            index for index, line in enumerate(payload.lines) if line.currency_amount is None
        ]
        if missing_currency_amounts:
            raise AppException(
                code="currency_amount_missing",
                message="currency_amount is required for all lines when currency_code is provided",
                details={"line_indexes": missing_currency_amounts},
                http_status=422,
            )

    ledger_repo = LedgerRepository(session=session)
    treasury_repo = TreasuryRepository(session=session)
    metadata = payload.entry_metadata or {}

    if payload.treasury_movement is not None:
        await validate_tenant_account_mapping(
            session,
            payload.tenant_id,
            ACCOUNT_MAPPING_REQUIREMENTS["treasury_movement"],
        )

    entry = await ledger_repo.create_journal_entry(
        tenant_id=payload.tenant_id,
        entry_date=payload.date,
        description=payload.description,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        currency_code=currency_code,
        fx_rate=payload.fx_rate,
    )

    for line in payload.lines:
        await ledger_repo.create_journal_entry_line(
            tenant_id=payload.tenant_id,
            journal_entry_id=entry.id,
            account_id=line.account_id,
            debit=Decimal(str(line.debit or 0)),
            credit=Decimal(str(line.credit or 0)),
            entity_type=line.entity_type,
            entity_id=line.entity_id,
            reference_type=line.reference_type,
            reference_id=line.reference_id,
            description=line.description,
            currency_amount=(Decimal(str(line.currency_amount)) if line.currency_amount is not None else None),
        )

    treasury_tx_id = None
    if payload.treasury_movement is not None:
        treasury_id = payload.treasury_movement.treasury_id
        if treasury_id is None:
            treasury_id = await treasury_repo.get_default_treasury_id(tenant_id=payload.tenant_id)
        if treasury_id is None:
            raise ValueError("Treasury movement requested but no treasury is available for tenant")
        movement_type = payload.treasury_movement.movement_type or payload.treasury_movement.reference_type
        if movement_type is None:
            movement_type = "disbursement"
        treasury_tx = await treasury_repo.create_transaction(
            tenant_id=payload.tenant_id,
            treasury_id=treasury_id,
            amount=payload.treasury_movement.amount,
            direction=payload.treasury_movement.direction,
            reference_type=payload.treasury_movement.reference_type,
            reference_id=payload.treasury_movement.reference_id,
            journal_entry_id=entry.id,
            movement_type=movement_type,
            party_type=payload.treasury_movement.party_type,
            party_id=payload.treasury_movement.party_id,
            reversed_of_id=payload.treasury_movement.reversed_of_id,
            is_reversed=bool(payload.treasury_movement.reversed_of_id),
        )
        treasury_tx_id = treasury_tx.id

    if metadata.get("treasury_transaction_id"):
        entry.treasury_transaction_id = metadata["treasury_transaction_id"]
    elif treasury_tx_id:
        entry.treasury_transaction_id = treasury_tx_id

    if metadata.get("adjusted_of_id"):
        entry.adjusted_of_id = metadata["adjusted_of_id"]
    if metadata.get("reversed_of_id"):
        entry.reversed_of_id = metadata["reversed_of_id"]
    if metadata.get("idempotency_key"):
        entry.idempotency_key = metadata["idempotency_key"]
    if metadata.get("adjustment_reason"):
        entry.adjustment_reason = metadata["adjustment_reason"]
    if metadata.get("is_reversed"):
        entry.is_reversed = True
    if metadata.get("is_voided"):
        entry.is_voided = True
    if metadata.get("voided_at"):
        entry.voided_at = metadata["voided_at"]
    if metadata.get("voided_by_user_id"):
        entry.voided_by_user_id = metadata["voided_by_user_id"]
    if metadata.get("voided_reason"):
        entry.voided_reason = metadata["voided_reason"]

    audit_log = build_audit_log(
        tenant_id=payload.tenant_id,
        actor_id=payload.actor_id,
        action="record_financial_transaction",
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        details={
            "journal_entry_id": str(entry.id),
            "treasury_transaction_id": str(treasury_tx_id) if treasury_tx_id else None,
        },
    )
    audit_log = await ledger_repo.write_audit_log(audit_log)

    if commit:
        await ledger_repo.commit()

    return RecordFinancialTransactionOutput(
        journal_entry_id=entry.id,
        treasury_transaction_id=treasury_tx_id,
        audit_log_id=audit_log.id,
    )


__all__ = ["record_financial_transaction"]
