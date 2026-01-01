from __future__ import annotations

from app.models.activity_log import ActivityLog
from app.models.ai_insight import AiInsight
from app.models.ai_run import AiRun
from app.models.audit_log import AuditLog
from app.models.billing_plan import BillingPlan
from app.models.customer import Customer
from app.models.data_snapshot import DataSnapshot
from app.models.debt import Debt
from app.models.debt_payment import DebtPayment
from app.models.employee import Employee
from app.models.error_event import ErrorEvent
from app.models.feedback import Feedback
from app.models.gdpr_request import GdprRequest
from app.models.ml_prediction import MlPrediction
from app.models.portal_token import PortalToken
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.stripe_event import StripeEvent
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig
from app.models.tenant_daily_usage import TenantDailyUsage
from app.models.tenant_subscription import TenantSubscription
from app.models.treasury import Treasury
from app.models.treasury_transaction import TreasuryTransaction
from app.models.user import User

ALL_MODELS = [
    Tenant,
    Role,
    User,
    Customer,
    Supplier,
    Employee,
    RefreshToken,
    ActivityLog,
    AiRun,
    AiInsight,
    MlPrediction,
    DataSnapshot,
    AuditLog,
    TenantDailyUsage,
    Debt,
    DebtPayment,
    ErrorEvent,
    TenantConfig,
    Feedback,
    BillingPlan,
    GdprRequest,
    PortalToken,
    TenantSubscription,
    StripeEvent,
    Treasury,
    TreasuryTransaction,
]


__all__ = [
    "Tenant",
    "Role",
    "User",
    "Customer",
    "Supplier",
    "Employee",
    "RefreshToken",
    "ActivityLog",
    "AiRun",
    "AiInsight",
    "MlPrediction",
    "DataSnapshot",
    "AuditLog",
    "TenantDailyUsage",
    "Debt",
    "DebtPayment",
    "ErrorEvent",
    "TenantConfig",
    "Feedback",
    "BillingPlan",
    "GdprRequest",
    "PortalToken",
    "TenantSubscription",
    "StripeEvent",
    "Treasury",
    "TreasuryTransaction",
    "ALL_MODELS",
]
