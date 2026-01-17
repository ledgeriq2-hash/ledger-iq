from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.services.audit_service import AuditService
from app.services.period_guard import PeriodGuard

STATUS_DRAFT = "Draft"
STATUS_POSTED = "Posted"
STATUS_REVERSED = "Reversed"
DEFAULT_BASE_CURRENCY = "USD"


@dataclass(slots=True)
class LedgerService:
    session: AsyncSession
    tenant_id: uuid.UUID
    actor_id: uuid.UUID | None = None

    def determine_period(self, entry_date: date) -> tuple[int, int]:
        return entry_date.year, entry_date.month

    def _generate_entry_no(self, entry_date: date) -> str:
        stamp = entry_date.strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:8].upper()
        return f"JE-{stamp}-{suffix}"

    def _quantize(self, value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _normalize_currency(self, currency: str | None) -> str:
        candidate = (currency or "").strip().upper()
        return candidate or DEFAULT_BASE_CURRENCY

    def _compute_base_amounts(
        self,
        *,
        debit: Decimal,
        credit: Decimal,
        line_currency: str,
        fx_rate: Decimal | None,
        base_currency: str,
    ) -> tuple[Decimal, Decimal]:
        if line_currency != base_currency:
            if fx_rate is None:
                raise AppException(
                    code="fx_rate_required",
                    message="FX rate is required when line currency differs from base currency",
                    http_status=422,
                )
            debit_base = self._quantize(debit * fx_rate)
            credit_base = self._quantize(credit * fx_rate)
            return debit_base, credit_base
        return debit, credit

    def validate_lines(self, lines: list[JournalLine], base_currency: str) -> list[dict]:
        if not lines:
            raise AppException(
                code="journal_lines_required",
                message="Journal entry requires at least one line",
                http_status=422,
            )

        normalized: list[dict] = []
        for line in lines:
            debit = self._quantize(getattr(line, "debit_amount", 0) or 0)
            credit = self._quantize(getattr(line, "credit_amount", 0) or 0)

            if debit <= 0 and credit <= 0:
                raise AppException(
                    code="journal_line_zero",
                    message="Journal entry lines must have a debit or credit amount",
                    http_status=422,
                )
            if debit > 0 and credit > 0:
                raise AppException(
                    code="journal_line_both_sides",
                    message="Journal entry lines cannot have both debit and credit amounts",
                    http_status=422,
                )

            raw_line_currency = getattr(line, "line_currency", None)
            line_currency = (raw_line_currency or "").strip().upper()
            if not line_currency:
                raise AppException(
                    code="journal_line_currency_required",
                    message="Line currency is required",
                    http_status=422,
                )

            fx_rate = getattr(line, "fx_rate", None)
            if fx_rate is not None:
                fx_rate = Decimal(str(fx_rate))

            debit_base, credit_base = self._compute_base_amounts(
                debit=debit,
                credit=credit,
                line_currency=line_currency,
                fx_rate=fx_rate,
                base_currency=base_currency,
            )

            normalized.append(
                {
                    "account_id": line.account_id,
                    "debit_amount": debit,
                    "credit_amount": credit,
                    "line_currency": line_currency,
                    "fx_rate": fx_rate,
                    "debit_base": debit_base,
                    "credit_base": credit_base,
                    "memo": getattr(line, "memo", None),
                    "dimensions": getattr(line, "dimensions", None),
                    "tax_code": getattr(line, "tax_code", None),
                }
            )
        return normalized

    def compute_base_totals(self, lines: list[dict]) -> tuple[Decimal, Decimal]:
        debit_total = sum((line["debit_base"] for line in lines), Decimal("0.00"))
        credit_total = sum((line["credit_base"] for line in lines), Decimal("0.00"))
        return self._quantize(debit_total), self._quantize(credit_total)

    async def _load_entry(self, entry_id: uuid.UUID, *, include_lines: bool = False) -> JournalEntry:
        stmt = select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.tenant_id == self.tenant_id,
        )
        if include_lines:
            stmt = stmt.options(selectinload(JournalEntry.ledger_lines))
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if not entry:
            raise AppException(
                code="journal_entry_not_found",
                message="Journal entry not found",
                http_status=404,
            )
        return entry

    async def create_manual_entry(
        self,
        *,
        entry_date: date,
        base_currency: str,
        memo: str | None,
        source_type: str,
        source_id: uuid.UUID | None,
        lines: list,
    ) -> JournalEntry:
        normalized_currency = self._normalize_currency(base_currency)
        normalized_lines = self.validate_lines(lines, normalized_currency)
        debit_total, credit_total = self.compute_base_totals(normalized_lines)
        period_year, period_month = self.determine_period(entry_date)

        entry = JournalEntry(
            tenant_id=self.tenant_id,
            entry_no=self._generate_entry_no(entry_date),
            entry_date=entry_date,
            date=entry_date,
            event_date=entry_date,
            posting_date=None,
            period_year=period_year,
            period_month=period_month,
            status=STATUS_DRAFT,
            source_type=source_type or "manual",
            source_id=source_id,
            memo=memo,
            description=memo,
            base_currency=normalized_currency,
            total_debit_base=debit_total,
            total_credit_base=credit_total,
            is_posted=False,
            created_by=self.actor_id,
            currency_code=normalized_currency,
        )
        self.session.add(entry)
        await self.session.flush()

        for index, line in enumerate(normalized_lines, start=1):
            self.session.add(
                JournalLine(
                    tenant_id=self.tenant_id,
                    entry_id=entry.id,
                    line_no=index,
                    account_id=line["account_id"],
                    debit_amount=line["debit_amount"],
                    credit_amount=line["credit_amount"],
                    line_currency=line["line_currency"],
                    fx_rate=line["fx_rate"],
                    debit_base=line["debit_base"],
                    credit_base=line["credit_base"],
                    memo=line["memo"],
                    dimensions=line["dimensions"],
                    tax_code=line["tax_code"],
                )
            )

        await self.session.commit()
        return await self._load_entry(entry.id, include_lines=True)

    async def post_entry(self, entry_id: uuid.UUID) -> JournalEntry:
        entry = await self._load_entry(entry_id, include_lines=True)
        if entry.status != STATUS_DRAFT:
            raise AppException(
                code="journal_post_invalid_status",
                message="Only draft entries can be posted",
                http_status=409,
            )

        guard = PeriodGuard(session=self.session)
        await guard.assert_open(tenant_id=self.tenant_id, entry_date=entry.entry_date)

        base_currency = self._normalize_currency(entry.base_currency)
        normalized_lines = self.validate_lines(entry.ledger_lines, base_currency)
        for line, normalized in zip(entry.ledger_lines, normalized_lines):
            line.debit_base = normalized["debit_base"]
            line.credit_base = normalized["credit_base"]

        debit_total, credit_total = self.compute_base_totals(normalized_lines)
        if debit_total != credit_total:
            raise AppException(
                code="journal_not_balanced",
                message="Journal entry is not balanced (debits != credits)",
                details={"debit_total": str(debit_total), "credit_total": str(credit_total)},
                http_status=422,
            )

        period_year, period_month = self.determine_period(entry.entry_date)
        now = datetime.now(UTC)

        entry.status = STATUS_POSTED
        entry.posting_date = now
        entry.posted_at = now
        entry.period_year = period_year
        entry.period_month = period_month
        entry.total_debit_base = debit_total
        entry.total_credit_base = credit_total
        entry.is_posted = True
        entry.base_currency = base_currency
        entry.source_type = entry.source_type or "manual"
        entry.date = entry.entry_date
        entry.event_date = entry.entry_date
        if not entry.entry_no:
            entry.entry_no = self._generate_entry_no(entry.entry_date)

        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="journal.post",
            entity_type="journal_entries",
            entity_id=str(entry.id),
            after={"status": entry.status, "posted_at": entry.posted_at.isoformat() if entry.posted_at else None},
            period_year=entry.period_year,
            period_month=entry.period_month,
            commit=False,
        )
        await self.session.commit()
        return await self._load_entry(entry.id, include_lines=True)

    async def reverse_entry(self, entry_id: uuid.UUID, *, reason: str) -> JournalEntry:
        if not reason or not reason.strip():
            raise AppException(
                code="journal_reverse_reason_required",
                message="Reversal reason is required",
                http_status=422,
            )

        entry = await self._load_entry(entry_id, include_lines=True)
        if entry.status == STATUS_REVERSED or entry.is_reversed:
            raise AppException(
                code="journal_already_reversed",
                message="Journal entry has already been reversed",
                http_status=409,
            )
        if entry.status != STATUS_POSTED:
            raise AppException(
                code="journal_reverse_invalid_status",
                message="Only posted entries can be reversed",
                http_status=409,
            )

        # MUST check lock on the ORIGINAL entry's entry_date per Sprint 2 spec.
        guard = PeriodGuard(session=self.session)
        await guard.assert_open(tenant_id=self.tenant_id, entry_date=entry.entry_date)

        reversal_date = date.today()
        base_currency = self._normalize_currency(entry.base_currency)
        normalized_lines = self.validate_lines(entry.ledger_lines, base_currency)

        debit_total, credit_total = self.compute_base_totals(normalized_lines)
        if debit_total != credit_total:
            raise AppException(
                code="journal_not_balanced",
                message="Journal entry is not balanced (debits != credits)",
                details={"debit_total": str(debit_total), "credit_total": str(credit_total)},
                http_status=422,
            )

        period_year, period_month = self.determine_period(reversal_date)
        now = datetime.now(UTC)

        reversal_entry = JournalEntry(
            tenant_id=self.tenant_id,
            entry_no=self._generate_entry_no(reversal_date),
            entry_date=reversal_date,
            date=reversal_date,
            event_date=reversal_date,
            posting_date=now,
            posted_at=now,
            period_year=period_year,
            period_month=period_month,
            status=STATUS_POSTED,
            source_type="reversal",
            source_id=entry.id,
            memo=reason,
            description=f"Reversal of {entry.entry_no}",
            base_currency=base_currency,
            total_debit_base=debit_total,
            total_credit_base=credit_total,
            reversal_of_entry_id=entry.id,
            reversed_of_id=entry.id,
            created_by=self.actor_id,
            is_posted=True,
            currency_code=base_currency,
        )
        self.session.add(reversal_entry)
        await self.session.flush()

        for index, line in enumerate(normalized_lines, start=1):
            self.session.add(
                JournalLine(
                    tenant_id=self.tenant_id,
                    entry_id=reversal_entry.id,
                    line_no=index,
                    account_id=line["account_id"],
                    debit_amount=line["credit_amount"],
                    credit_amount=line["debit_amount"],
                    line_currency=line["line_currency"],
                    fx_rate=line["fx_rate"],
                    debit_base=line["credit_base"],
                    credit_base=line["debit_base"],
                    memo=f"Reversal: {line['memo']}" if line["memo"] else None,
                    dimensions=line["dimensions"],
                    tax_code=line["tax_code"],
                )
            )

        entry.status = STATUS_REVERSED
        entry.is_reversed = True

        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="journal.reverse",
            entity_type="journal_entries",
            entity_id=str(entry.id),
            reason=reason,
            after={"reversal_entry_id": str(reversal_entry.id)},
            period_year=reversal_entry.period_year,
            period_month=reversal_entry.period_month,
            commit=False,
        )

        await self.session.commit()
        return await self._load_entry(reversal_entry.id, include_lines=True)


__all__ = ["LedgerService", "STATUS_DRAFT", "STATUS_POSTED", "STATUS_REVERSED"]
