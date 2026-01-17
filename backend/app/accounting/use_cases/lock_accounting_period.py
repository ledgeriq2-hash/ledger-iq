from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.repositories.period_lock_repo import PeriodLockRepository
from app.core.exceptions import AppException
from app.models.accounting_period_lock import AccountingPeriodLock
from app.services.audit_service import AuditService


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
    audit = AuditService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    await audit.log(
        action="period.lock",
        entity_type="accounting_period_locks",
        entity_id=str(lock.id),
        after={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        commit=False,
    )
    if commit:
        await session.commit()
        await session.refresh(lock)
    return lock


async def unlock_accounting_period(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    lock_id: UUID,
    actor_id: UUID | None,
    commit: bool = True,
) -> AccountingPeriodLock:
    result = await session.execute(
        select(AccountingPeriodLock).where(
            AccountingPeriodLock.id == lock_id,
            AccountingPeriodLock.tenant_id == tenant_id,
        )
    )
    lock = result.scalar_one_or_none()
    if not lock:
        raise AppException(
            code="period_lock_not_found",
            message="Accounting period lock not found",
            http_status=404,
        )
    audit = AuditService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    await audit.log(
        action="period.unlock",
        entity_type="accounting_period_locks",
        entity_id=str(lock.id),
        before={"start_date": lock.start_date.isoformat(), "end_date": lock.end_date.isoformat()},
        commit=False,
    )
    await session.delete(lock)
    if commit:
        await session.commit()
    return lock


__all__ = ["lock_accounting_period", "unlock_accounting_period"]

