from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    admin,
    auth,
    customers,
    employees,
    expenses,
    invoices,
    journal_entries,
    billing,
    notifications,
    payments,
    portal,
    feedback,
    products,
    inventory,
    onboarding,
    gdpr,
    reports,
    roles,
    suppliers,
    tenants,
    users,
    recurring_invoices,
)

router = APIRouter(prefix="/api")

router.include_router(auth.router, prefix="/v1", tags=["auth"])
router.include_router(users.router, prefix="/v1", tags=["users"])
router.include_router(roles.router, prefix="/v1", tags=["roles"])
router.include_router(tenants.router, prefix="/v1", tags=["tenants"])
router.include_router(customers.router, prefix="/v1", tags=["customers"])
router.include_router(suppliers.router, prefix="/v1", tags=["suppliers"])
router.include_router(employees.router, prefix="/v1", tags=["employees"])
router.include_router(products.router, prefix="/v1", tags=["products"])
router.include_router(invoices.router, prefix="/v1", tags=["invoices"])
router.include_router(payments.router, prefix="/v1", tags=["payments"])
router.include_router(expenses.router, prefix="/v1", tags=["expenses"])
router.include_router(journal_entries.router, prefix="/v1", tags=["journal_entries"])
router.include_router(billing.router, prefix="/v1", tags=["billing"])
router.include_router(onboarding.router, prefix="/v1", tags=["onboarding"])
router.include_router(gdpr.router, prefix="/v1", tags=["gdpr"])
router.include_router(notifications.router, prefix="/v1", tags=["notifications"])
router.include_router(portal.router, prefix="/v1", tags=["portal"])
router.include_router(reports.router, prefix="/v1", tags=["reports"])
router.include_router(ai.router, prefix="/v1", tags=["ai"])
router.include_router(admin.router, prefix="/v1", tags=["admin"])
router.include_router(feedback.router, prefix="/v1", tags=["feedback"])
router.include_router(recurring_invoices.router, prefix="/v1", tags=["recurring_invoices"])
router.include_router(inventory.router, prefix="/v1", tags=["inventory"])

__all__ = ["router"]
