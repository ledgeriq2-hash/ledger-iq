from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.treasury_cash_transaction import CashTransactionStatus, CashTransactionType, TreasuryCashTransaction


@dataclass(slots=True)
class CashTransactionRepository:
    session: AsyncSession

    async def create_draft(
        self,
        *,
        tenant_id: UUID,
        transaction_type: CashTransactionType,
        amount: Decimal,
        posting_date: date,
        description: str | None = None,
        cash_account_id: UUID | None = None,
        counterparty_account_id: UUID | None = None,
        from_cash_account_id: UUID | None = None,
        to_cash_account_id: UUID | None = None,
    ) -> TreasuryCashTransaction:
        tx = TreasuryCashTransaction(
            tenant_id=tenant_id,
            transaction_type=transaction_type,
            status=CashTransactionStatus.DRAFT,
            amount=amount,
            posting_date=posting_date,
            description=description,
            cash_account_id=cash_account_id,
            counterparty_account_id=counterparty_account_id,
            from_cash_account_id=from_cash_account_id,
            to_cash_account_id=to_cash_account_id,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def get(self, *, tenant_id: UUID, transaction_id: UUID) -> TreasuryCashTransaction | None:
        result = await self.session.execute(
            select(TreasuryCashTransaction).where(
                TreasuryCashTransaction.id == transaction_id,
                TreasuryCashTransaction.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        tenant_id: UUID,
        transaction_type: CashTransactionType | None = None,
        status: CashTransactionStatus | None = None,
        cash_account_id: UUID | None = None,
        counterparty_account_id: UUID | None = None,
        from_cash_account_id: UUID | None = None,
        to_cash_account_id: UUID | None = None,
        posting_date_start: date | None = None,
        posting_date_end: date | None = None,
    ) -> Sequence[TreasuryCashTransaction]:
        stmt = select(TreasuryCashTransaction).where(TreasuryCashTransaction.tenant_id == tenant_id)

        if transaction_type:
            stmt = stmt.where(TreasuryCashTransaction.transaction_type == transaction_type)
        if status:
            stmt = stmt.where(TreasuryCashTransaction.status == status)
        if cash_account_id:
            stmt = stmt.where(TreasuryCashTransaction.cash_account_id == cash_account_id)
        if counterparty_account_id:
            stmt = stmt.where(TreasuryCashTransaction.counterparty_account_id == counterparty_account_id)
        if from_cash_account_id:
            stmt = stmt.where(TreasuryCashTransaction.from_cash_account_id == from_cash_account_id)
        if to_cash_account_id:
            stmt = stmt.where(TreasuryCashTransaction.to_cash_account_id == to_cash_account_id)
        if posting_date_start:
            stmt = stmt.where(TreasuryCashTransaction.posting_date >= posting_date_start)
        if posting_date_end:
            stmt = stmt.where(TreasuryCashTransaction.posting_date <= posting_date_end)

        stmt = stmt.order_by(TreasuryCashTransaction.posting_date.desc(), TreasuryCashTransaction.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()


__all__ = ["CashTransactionRepository"]
