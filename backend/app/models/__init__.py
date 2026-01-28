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
from app.models.customer_receipt import CustomerReceipt, CustomerReceiptStatus
from app.models.customer_receipt_allocation import CustomerReceiptAllocation
from app.models.data_snapshot import DataSnapshot
from app.models.dimension import Dimension
from app.models.dimension_value import DimensionValue
from app.models.employee import Employee, EmployeeStatus
from app.models.error_event import ErrorEvent
from app.models.expense import Expense
from app.models.feedback import Feedback
from app.models.fx_revaluation_line import FXRevaluationLine
from app.models.fx_revaluation_run import FXRevaluationRun, FXRevaluationStatus
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
from app.models.product import Product, ProductStatus
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceStatus
from app.models.purchase_invoice_line import PurchaseInvoiceLine
from app.models.recurring_invoice import RecurringInvoice
from app.models.refresh_token import RefreshToken
from app.models.reports_cache import ReportsCache
from app.models.role import Role
from app.models.sales_invoice import SalesInvoice, SalesInvoiceStatus
from app.models.sales_invoice_line import SalesInvoiceLine
from app.models.stock_balance import StockBalance
from app.models.stock_move import StockMove, StockMoveDirection, StockMoveSourceType
from app.models.stock_movement import StockMovement
from app.models.stripe_event import StripeEvent
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig
from app.models.tenant_daily_usage import TenantDailyUsage
from app.models.tenant_subscription import TenantSubscription
from app.models.treasury import Treasury
from app.models.treasury_cash_account import TreasuryCashAccount
from app.models.treasury_cash_transaction import (
    CashTransactionStatus,
    CashTransactionType,
    TreasuryCashTransaction,
)
from app.models.treasury_transaction import TreasuryTransaction
from app.models.unit import InventoryUnit, Unit
from app.models.unit_conversion import UnitConversion
from app.models.user import User
from app.models.vendor import Vendor, VendorStatus
from app.models.vendor_payment import VendorPayment, VendorPaymentStatus
from app.models.vendor_payment_allocation import VendorPaymentAllocation

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
    CustomerReceipt,
    CustomerReceiptAllocation,
    CustomerReceiptStatus,
    DataSnapshot,
    Dimension,
    DimensionValue,
    Employee,
    EmployeeStatus,
    ErrorEvent,
    Expense,
    Feedback,
    FXRevaluationLine,
    FXRevaluationRun,
    FXRevaluationStatus,
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
    ProductStatus,
    PurchaseInvoice,
    PurchaseInvoiceLine,
    RecurringInvoice,
    RefreshToken,
    ReportsCache,
    Role,
    SalesInvoice,
    SalesInvoiceLine,
    StockMovement,
    StockMove,
    StockBalance,
    StripeEvent,
    Supplier,
    Tenant,
    TenantConfig,
    TenantDailyUsage,
    TenantSubscription,
    Treasury,
    TreasuryCashAccount,
    TreasuryCashTransaction,
    TreasuryTransaction,
    InventoryUnit,
    Unit,
    UnitConversion,
    User,
    Vendor,
    VendorPayment,
    VendorPaymentAllocation,
    VendorPaymentStatus,
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
    "CustomerReceipt",
    "CustomerReceiptAllocation",
    "CustomerReceiptStatus",
    "DataSnapshot",
    "Dimension",
    "DimensionValue",
    "Employee",
    "EmployeeStatus",
    "ErrorEvent",
    "Expense",
    "Feedback",
    "FXRevaluationLine",
    "FXRevaluationRun",
    "FXRevaluationStatus",
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
    "ProductStatus",
    "PurchaseInvoice",
    "PurchaseInvoiceLine",
    "PurchaseInvoiceStatus",
    "RecurringInvoice",
    "RefreshToken",
    "ReportsCache",
    "Role",
    "SalesInvoice",
    "SalesInvoiceLine",
    "SalesInvoiceStatus",
    "StockMovement",
    "StockMove",
    "StockMoveDirection",
    "StockMoveSourceType",
    "StockBalance",
    "StripeEvent",
    "Supplier",
    "Tenant",
    "TenantConfig",
    "TenantDailyUsage",
    "TenantSubscription",
    "Treasury",
    "TreasuryCashAccount",
    "CashTransactionStatus",
    "CashTransactionType",
    "TreasuryCashTransaction",
    "TreasuryTransaction",
    "InventoryUnit",
    "Unit",
    "UnitConversion",
    "User",
    "Vendor",
    "VendorStatus",
    "VendorPayment",
    "VendorPaymentAllocation",
    "VendorPaymentStatus",
    "ALL_MODELS",
]
