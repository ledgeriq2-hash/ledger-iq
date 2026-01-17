from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.repositories.period_lock_repo import PeriodLockRepository
from app.core.exceptions import AppException


@dataclass(slots=True)
class PeriodGuard:
    session: AsyncSession

    async def assert_open(self, *, tenant_id: UUID, entry_date: date) -> None:
        repo = PeriodLockRepository(session=self.session)
        if await repo.is_locked(tenant_id=tenant_id, entry_date=entry_date):
            raise AppException(
                code="accounting_period_locked",
                message="Accounting period is locked for the provided date",
                http_status=409,
            )


__all__ = ["PeriodGuard"]
