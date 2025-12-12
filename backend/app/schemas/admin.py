from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema
from app.schemas.error_event import ErrorEventPublic
from app.schemas.usage import TenantDailyUsagePublic
from app.schemas.feedback import FeedbackPublic


class TenantAdminSummary(BaseSchema):
    id: UUID
    name: str
    slug: str
    created_at: datetime
    owner_email: str | None = None
    is_soft_launch: bool = False
    plan_code: str | None = None
    subscription_status: str | None = None


class TenantOverviewResponse(BaseSchema):
    tenant: TenantAdminSummary
    usage: list[TenantDailyUsagePublic]
    errors: list[ErrorEventPublic]
    feedback: list[FeedbackPublic]
    totals: dict
    last_login_at: datetime | None = None
    billing: dict | None = None


__all__ = ["TenantAdminSummary", "TenantOverviewResponse"]
