from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenantDailyUsage(BaseModel):
    __tablename__ = "tenant_daily_usage"

    date: Mapped[date] = mapped_column(Date, nullable=False)
    invoices_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payments_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    customers_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_logins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_tenant_daily_usage_tenant_date", "tenant_id", "date", unique=True),)


__all__ = ["TenantDailyUsage"]
