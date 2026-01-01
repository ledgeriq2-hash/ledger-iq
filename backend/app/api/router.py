from __future__ import annotations

from fastapi import APIRouter

from app.api import settings
from app.api.v1 import (
    accounting_periods,
    admin,
    ai,
    auth,
    billing,
    customers,
    dashboard,
    debts,
    dev,
    employees,
    expenses,
    feedback,
    gdpr,
    inventory,
    invoices,
    journal_entries,
    treasury,
    ml,
    notifications,
    onboarding,
    payments,
    portal,
    products,
    recurring_invoices,
    reports,
    roles,
    suppliers,
    tenants,
    users,
)

router = APIRouter(prefix="/api")

router.include_router(settings.router, tags=["settings"])

router.include_router(dashboard.router, prefix="/v1", tags=["dashboard"])
router.include_router(portal.contract_router, tags=["portal"])

router.include_router(auth.router, prefix="/v1", tags=["auth"])
router.include_router(users.router, prefix="/v1", tags=["users"])
router.include_router(roles.router, prefix="/v1", tags=["roles"])
router.include_router(tenants.router, prefix="/v1", tags=["tenants"])
router.include_router(customers.router, prefix="/v1", tags=["customers"])
router.include_router(suppliers.router, prefix="/v1", tags=["suppliers"])
router.include_router(debts.router, prefix="/v1", tags=["debts"])
router.include_router(employees.router, prefix="/v1", tags=["employees"])
router.include_router(products.router, prefix="/v1", tags=["products"])
router.include_router(invoices.router, prefix="/v1", tags=["invoices"])
router.include_router(payments.router, prefix="/v1", tags=["payments"])
router.include_router(expenses.router, prefix="/v1", tags=["expenses"])
router.include_router(journal_entries.router, prefix="/v1", tags=["journal_entries"])
router.include_router(treasury.router, prefix="/v1", tags=["treasury"])
router.include_router(accounting_periods.router, prefix="/v1", tags=["accounting_periods"])
router.include_router(billing.router, prefix="/v1", tags=["billing"])
router.include_router(onboarding.router, prefix="/v1", tags=["onboarding"])
router.include_router(gdpr.router, prefix="/v1", tags=["gdpr"])
router.include_router(notifications.router, prefix="/v1", tags=["notifications"])
router.include_router(portal.router, prefix="/v1", tags=["portal"])
router.include_router(reports.router, prefix="/v1", tags=["reports"])
router.include_router(ai.router, prefix="/v1", tags=["ai"])
router.include_router(ml.router, prefix="/v1", tags=["ml"])
router.include_router(dev.router, prefix="/v1", tags=["dev"])
router.include_router(admin.router, prefix="/v1", tags=["admin"])
router.include_router(feedback.router, prefix="/v1", tags=["feedback"])
router.include_router(recurring_invoices.router, prefix="/v1", tags=["recurring_invoices"])
router.include_router(inventory.router, prefix="/v1", tags=["inventory"])

__all__ = ["router"]
