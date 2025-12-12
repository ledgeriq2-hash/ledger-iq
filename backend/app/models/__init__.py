from __future__ import annotations

from app.models.activity_log import ActivityLog
from app.models.audit_log import AuditLog
from app.models.feedback import Feedback
from app.models.error_event import ErrorEvent
from app.models.billing_plan import BillingPlan
from app.models.tenant_subscription import TenantSubscription
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.tenant_daily_usage import TenantDailyUsage
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig
from app.models.user import User

ALL_MODELS = [
    Tenant,
    Role,
    User,
    RefreshToken,
    ActivityLog,
    AuditLog,
    TenantDailyUsage,
    ErrorEvent,
    TenantConfig,
    Feedback,
    BillingPlan,
    TenantSubscription,
]


__all__ = [
    "Tenant",
    "Role",
    "User",
    "RefreshToken",
    "ActivityLog",
    "AuditLog",
    "TenantDailyUsage",
    "ErrorEvent",
    "TenantConfig",
    "Feedback",
    "BillingPlan",
    "TenantSubscription",
    "ALL_MODELS",
]
