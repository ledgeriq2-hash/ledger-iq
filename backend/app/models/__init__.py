from __future__ import annotations

from app.models.activity_log import ActivityLog
from app.models.ai_log import AiLog
from app.models.ai_insight import AiInsight
from app.models.ai_run import AiRun
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.accounting_period_lock import AccountingPeriodLock
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.billing_plan import BillingPlan
from app.models.cashflow_category import CashflowCategory
from app.models.chart_of_account import ChartOfAccount
from app.models.customer import Customer
from app.models.data_snapshot import DataSnapshot
from app.models.dimension import Dimension
from app.models.dimension_value import DimensionValue
from app.models.employee import Employee, EmployeeStatus
from app.models.error_event import ErrorEvent
from app.models.expense import Expense
from app.models.feedback import Feedback
from app.models.gdpr_request import GdprRequest
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
from app.models.journal_line import JournalLine
from app.models.journal_line_dimension import JournalLineDimension
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.portal_token import PortalToken
from app.models.product import Product
from app.models.recurring_invoice import RecurringInvoice
from app.models.refresh_token import RefreshToken
from app.models.reports_cache import ReportsCache
from app.models.role import Role
from app.models.stock_movement import StockMovement
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
    ActivityLog,
    AiLog,
    AiInsight,
    AiRun,
    Account,
    AccountMapping,
    AccountingPeriodLock,
    Attachment,
    AuditLog,
    BillingPlan,
    CashflowCategory,
    ChartOfAccount,
    Customer,
    DataSnapshot,
    Dimension,
    DimensionValue,
    Employee,
    EmployeeStatus,
    ErrorEvent,
    Expense,
    Feedback,
    GdprRequest,
    Invoice,
    InvoiceItem,
    JournalEntry,
    JournalEntryLine,
    JournalLine,
    JournalLineDimension,
    Notification,
    Payment,
    PortalToken,
    Product,
    RecurringInvoice,
    RefreshToken,
    ReportsCache,
    Role,
    StockMovement,
    StripeEvent,
    Supplier,
    Tenant,
    TenantConfig,
    TenantDailyUsage,
    TenantSubscription,
    Treasury,
    TreasuryTransaction,
    User,
]


__all__ = [
    "ActivityLog",
    "AiLog",
    "AiInsight",
    "AiRun",
    "Account",
    "AccountMapping",
    "AccountingPeriodLock",
    "Attachment",
    "AuditLog",
    "BillingPlan",
    "CashflowCategory",
    "ChartOfAccount",
    "Customer",
    "DataSnapshot",
    "Dimension",
    "DimensionValue",
    "Employee",
    "EmployeeStatus",
    "ErrorEvent",
    "Expense",
    "Feedback",
    "GdprRequest",
    "Invoice",
    "InvoiceItem",
    "JournalEntry",
    "JournalEntryLine",
    "JournalLine",
    "JournalLineDimension",
    "Notification",
    "Payment",
    "PortalToken",
    "Product",
    "RecurringInvoice",
    "RefreshToken",
    "ReportsCache",
    "Role",
    "StockMovement",
    "StripeEvent",
    "Supplier",
    "Tenant",
    "TenantConfig",
    "TenantDailyUsage",
    "TenantSubscription",
    "Treasury",
    "TreasuryTransaction",
    "User",
    "ALL_MODELS",
]
