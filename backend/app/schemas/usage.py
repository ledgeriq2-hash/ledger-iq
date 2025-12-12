from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class TenantDailyUsagePublic(BaseSchema):
    id: UUID
    tenant_id: UUID
    date: date
    invoices_created: int
    payments_created: int
    customers_created: int
    total_logins: int
    last_activity_at: datetime | None


class TenantUsageResponse(BaseSchema):
    tenant_id: UUID
    usage: list[TenantDailyUsagePublic]


__all__ = ["TenantDailyUsagePublic", "TenantUsageResponse"]
