from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import BaseSchema, IDTimestampMixin


class PlanPublic(IDTimestampMixin):
    code: str
    name: str
    price_cents: int
    currency: str
    interval: str
    limits_json: dict | None = None
    metadata_json: dict | None = None


class SubscriptionPublic(IDTimestampMixin):
    plan_code: str | None = None
    status: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    checkout_session_id: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    usage_json: dict | None = None


class BillingStatus(BaseSchema):
    plan: PlanPublic | None = None
    plan_code: str | None = None
    subscription: SubscriptionPublic | None = None
    usage: dict
    limits: dict


class BillingUsage(BaseSchema):
    invoices_this_month: int = 0
    ai_calls_this_month: int = 0
    storage_usage_mb: float = 0.0


class BillingLimits(BaseSchema):
    max_invoices_per_month: int | None = None
    max_ai_calls_per_month: int | None = None
    max_storage_mb: float | None = None


class BillingPlanInfo(BaseSchema):
    plan_code: str | None = None
    plan_name: str | None = None
    price: float | None = None
    currency: str | None = None
    billing_period: str | None = None


class BillingOverviewResponse(BaseSchema):
    plan: BillingPlanInfo | None = None
    usage: BillingUsage
    limits: BillingLimits
    stripe_customer_portal_url: str | None = None
    checkout_url: str | None = None
    metadata: dict[str, Any] | None = None


__all__ = [
    "PlanPublic",
    "SubscriptionPublic",
    "BillingStatus",
    "BillingUsage",
    "BillingLimits",
    "BillingPlanInfo",
    "BillingOverviewResponse",
]
