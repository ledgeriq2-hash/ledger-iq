from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.treasury_cash_account import TreasuryCashAccount


@dataclass(slots=True)
class CashAccountRepository:
    session: AsyncSession

    async def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        account_id: UUID,
        description: str | None = None,
    ) -> TreasuryCashAccount:
        account = TreasuryCashAccount(
            tenant_id=tenant_id,
            name=name,
            account_id=account_id,
            description=description,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def get(self, *, tenant_id: UUID, cash_account_id: UUID) -> TreasuryCashAccount | None:
        result = await self.session.execute(
            select(TreasuryCashAccount).where(
                TreasuryCashAccount.id == cash_account_id,
                TreasuryCashAccount.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, *, tenant_id: UUID) -> Sequence[TreasuryCashAccount]:
        result = await self.session.execute(
            select(TreasuryCashAccount)
            .where(TreasuryCashAccount.tenant_id == tenant_id)
            .order_by(TreasuryCashAccount.created_at.desc())
        )
        return result.scalars().all()


__all__ = ["CashAccountRepository"]
