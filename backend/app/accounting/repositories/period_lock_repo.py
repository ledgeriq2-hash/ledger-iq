from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_period_lock import AccountingPeriodLock


@dataclass(slots=True)
class PeriodLockRepository:
    session: AsyncSession

    async def is_locked(self, *, tenant_id: UUID, entry_date: date) -> bool:
        result = await self.session.execute(
            select(AccountingPeriodLock.id).where(
                AccountingPeriodLock.tenant_id == tenant_id,
                AccountingPeriodLock.start_date <= entry_date,
                AccountingPeriodLock.end_date >= entry_date,
            )
        )
        return result.first() is not None

    async def create_lock(
        self,
        *,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        actor_id: UUID | None,
    ) -> AccountingPeriodLock:
        lock = AccountingPeriodLock(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            locked_by=actor_id,
        )
        self.session.add(lock)
        await self.session.flush()
        return lock


__all__ = ["PeriodLockRepository"]

