from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine


@dataclass(slots=True)
class LedgerRepository:
    session: AsyncSession

    async def create_journal_entry(
        self,
        *,
        tenant_id: UUID,
        entry_date: date,
        description: str | None,
        reference_type: str,
        reference_id: UUID,
        currency_code: str | None = None,
        fx_rate: Decimal | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            tenant_id=tenant_id,
            date=entry_date,
            description=description,
            reference=reference_type,
            source_module=reference_type,
            source_id=reference_id,
            is_posted=True,
            currency_code=currency_code,
            fx_rate=fx_rate,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def create_journal_entry_line(
        self,
        *,
        tenant_id: UUID,
        journal_entry_id: UUID,
        account_id: UUID,
        debit: Decimal,
        credit: Decimal,
        entity_type: str | None,
        entity_id: UUID | None,
        reference_type: str,
        reference_id: UUID,
        description: str | None,
        currency_amount: Decimal | None = None,
    ) -> JournalEntryLine:
        line = JournalEntryLine(
            tenant_id=tenant_id,
            journal_entry_id=journal_entry_id,
            account_id=account_id,
            debit=debit,
            credit=credit,
            line_description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            reference_type=reference_type,
            reference_id=reference_id,
            currency_amount=currency_amount,
        )
        self.session.add(line)
        await self.session.flush()
        return line

    async def write_audit_log(self, audit_log: AuditLog) -> AuditLog:
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def commit(self) -> None:
        await self.session.commit()


__all__ = ["LedgerRepository"]
