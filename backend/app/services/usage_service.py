from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_daily_usage import TenantDailyUsage


async def _get_or_create_usage(session: AsyncSession, tenant_id: UUID, usage_date: date | None = None) -> TenantDailyUsage:
    usage_date = usage_date or date.today()
    result = await session.execute(
        select(TenantDailyUsage).where(TenantDailyUsage.tenant_id == tenant_id, TenantDailyUsage.date == usage_date)
    )
    usage = result.scalar_one_or_none()
    if usage:
        return usage
    usage = TenantDailyUsage(
        tenant_id=tenant_id,
        date=usage_date,
        invoices_created=0,
        payments_created=0,
        customers_created=0,
        total_logins=0,
        last_activity_at=datetime.now(timezone.utc),
    )
    session.add(usage)
    await session.flush()
    return usage


async def record_customer_created(session: AsyncSession, tenant_id: UUID) -> None:
    usage = await _get_or_create_usage(session, tenant_id)
    usage.customers_created += 1
    usage.last_activity_at = datetime.now(timezone.utc)
    await session.commit()


async def record_invoice_created(session: AsyncSession, tenant_id: UUID) -> None:
    usage = await _get_or_create_usage(session, tenant_id)
    usage.invoices_created += 1
    usage.last_activity_at = datetime.now(timezone.utc)
    await session.commit()


async def record_payment_created(session: AsyncSession, tenant_id: UUID) -> None:
    usage = await _get_or_create_usage(session, tenant_id)
    usage.payments_created += 1
    usage.last_activity_at = datetime.now(timezone.utc)
    await session.commit()


async def record_login(session: AsyncSession, tenant_id: UUID) -> None:
    usage = await _get_or_create_usage(session, tenant_id)
    usage.total_logins += 1
    usage.last_activity_at = datetime.now(timezone.utc)
    await session.commit()


async def fetch_recent_usage(session: AsyncSession, tenant_id: UUID, days: int = 30) -> list[TenantDailyUsage]:
    cutoff = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        select(TenantDailyUsage)
        .where(TenantDailyUsage.tenant_id == tenant_id, TenantDailyUsage.date >= cutoff)
        .order_by(TenantDailyUsage.date.desc())
    )
    return result.scalars().all()


__all__ = [
    "record_customer_created",
    "record_invoice_created",
    "record_payment_created",
    "record_login",
    "fetch_recent_usage",
]
