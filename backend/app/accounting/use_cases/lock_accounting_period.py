from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.repositories.period_lock_repo import PeriodLockRepository
from app.core.exceptions import AppException
from app.models.accounting_period_lock import AccountingPeriodLock


async def lock_accounting_period(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    actor_id: UUID | None,
    commit: bool = True,
) -> AccountingPeriodLock:
    if end_date < start_date:
        raise AppException(code="invalid_period", message="end_date must be on or after start_date", http_status=422)

    repo = PeriodLockRepository(session=session)
    lock = await repo.create_lock(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        actor_id=actor_id,
    )
    if commit:
        await session.commit()
        await session.refresh(lock)
    return lock


__all__ = ["lock_accounting_period"]

