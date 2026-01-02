from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chart_of_account import ChartOfAccount
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
from app.models.treasury_transaction import TreasuryTransaction


@dataclass(slots=True)
class StatementRepository:
    session: AsyncSession

    async def get_client_opening_balance(
        self,
        *,
        tenant_id: UUID,
        client_id: UUID,
        before_date: date,
    ) -> Decimal:
        return await self.get_entity_opening_balance(
            tenant_id=tenant_id,
            entity_type="client",
            entity_id=client_id,
            before_date=before_date,
        )

    async def list_client_lines(
        self,
        *,
        tenant_id: UUID,
        client_id: UUID,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict]:
        return await self.list_entity_lines(
            tenant_id=tenant_id,
            entity_type="client",
            entity_id=client_id,
            from_date=from_date,
            to_date=to_date,
        )

    async def get_entity_opening_balance(
        self,
        *,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_date: date,
    ) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(JournalEntryLine.debit - JournalEntryLine.credit), 0))
            .select_from(JournalEntryLine)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .where(
                JournalEntryLine.tenant_id == tenant_id,
                JournalEntryLine.entity_type == entity_type,
                JournalEntryLine.entity_id == entity_id,
                JournalEntry.date < before_date,
            )
        )
        return Decimal(str(result.scalar_one() or 0)).quantize(Decimal("0.01"))

    async def list_entity_lines(
        self,
        *,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict]:
        query = (
            select(
                JournalEntry.date.label("date"),
                JournalEntry.id.label("journal_entry_id"),
                JournalEntry.description.label("journal_description"),
                JournalEntryLine.id.label("line_id"),
                JournalEntryLine.account_id.label("account_id"),
                ChartOfAccount.code.label("account_code"),
                ChartOfAccount.name.label("account_name"),
                JournalEntryLine.debit.label("debit"),
                JournalEntryLine.credit.label("credit"),
                JournalEntryLine.line_description.label("line_description"),
                JournalEntryLine.reference_type.label("reference_type"),
                JournalEntryLine.reference_id.label("reference_id"),
                JournalEntry.treasury_transaction_id.label("treasury_transaction_id"),
                TreasuryTransaction.movement_type.label("movement_type"),
                JournalEntryLine.created_at.label("created_at"),
            )
            .select_from(JournalEntryLine)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .join(ChartOfAccount, ChartOfAccount.id == JournalEntryLine.account_id)
            .outerjoin(
                TreasuryTransaction,
                TreasuryTransaction.id == JournalEntry.treasury_transaction_id,
            )
            .where(
                JournalEntryLine.tenant_id == tenant_id,
                JournalEntryLine.entity_type == entity_type,
                JournalEntryLine.entity_id == entity_id,
            )
        )
        if from_date:
            query = query.where(JournalEntry.date >= from_date)
        if to_date:
            query = query.where(JournalEntry.date <= to_date)
        query = query.order_by(JournalEntry.date.asc(), JournalEntryLine.created_at.asc())

        result = await self.session.execute(query)
        rows = []
        for r in result.mappings().all():
            rows.append(
                {
                    "date": r["date"],
                    "journal_entry_id": r["journal_entry_id"],
                    "line_id": r["line_id"],
                    "account_id": r["account_id"],
                    "account_code": r["account_code"],
                    "account_name": r["account_name"],
                    "debit": Decimal(str(r["debit"] or 0)).quantize(Decimal("0.01")),
                    "credit": Decimal(str(r["credit"] or 0)).quantize(Decimal("0.01")),
                    "description": r["line_description"] or r["journal_description"],
                    "reference_type": r["reference_type"],
                    "reference_id": r["reference_id"],
                    "treasury_transaction_id": r["treasury_transaction_id"],
                    "movement_type": r["movement_type"],
                }
            )
        return rows


__all__ = ["StatementRepository"]
