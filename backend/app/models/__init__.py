from __future__ import annotations

from app.models.activity_log import ActivityLog
from app.models.ai_log import AiLog
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.billing_plan import BillingPlan
from app.models.cashflow_category import CashflowCategory
from app.models.chart_of_account import ChartOfAccount
from app.models.customer import Customer
from app.models.employee import Employee, EmployeeStatus
from app.models.error_event import ErrorEvent
from app.models.expense import Expense
from app.models.feedback import Feedback
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.portal_token import PortalToken
from app.models.product import Product
from app.models.recurring_invoice import RecurringInvoice
from app.models.refresh_token import RefreshToken
from app.models.reports_cache import ReportsCache
from app.models.role import Role
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig
from app.models.tenant_daily_usage import TenantDailyUsage
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User

ALL_MODELS = [
    ActivityLog,
    AiLog,
    Attachment,
    AuditLog,
    BillingPlan,
    CashflowCategory,
    ChartOfAccount,
    Customer,
    Employee,
    EmployeeStatus,
    ErrorEvent,
    Expense,
    Feedback,
    Invoice,
    InvoiceItem,
    JournalEntry,
    JournalEntryLine,
    Notification,
    Payment,
    PortalToken,
    Product,
    RecurringInvoice,
    RefreshToken,
    ReportsCache,
    Role,
    StockMovement,
    Supplier,
    Tenant,
    TenantConfig,
    TenantDailyUsage,
    TenantSubscription,
    User,
]


__all__ = [
    "ActivityLog",
    "AiLog",
    "Attachment",
    "AuditLog",
    "BillingPlan",
    "CashflowCategory",
    "ChartOfAccount",
    "Customer",
    "Employee",
    "EmployeeStatus",
    "ErrorEvent",
    "Expense",
    "Feedback",
    "Invoice",
    "InvoiceItem",
    "JournalEntry",
    "JournalEntryLine",
    "Notification",
    "Payment",
    "PortalToken",
    "Product",
    "RecurringInvoice",
    "RefreshToken",
    "ReportsCache",
    "Role",
    "StockMovement",
    "Supplier",
    "Tenant",
    "TenantConfig",
    "TenantDailyUsage",
    "TenantSubscription",
    "User",
    "ALL_MODELS",
]
