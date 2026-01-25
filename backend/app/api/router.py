from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api")


def _include(router_obj: APIRouter, *, prefix: str, tags: list[str]) -> None:
    if prefix:
        router.include_router(router_obj, prefix=prefix, tags=tags)
    else:
        router.include_router(router_obj, tags=tags)


from app.api.v1.accounts import router as accounts_router
from app.api.v1.customers import router as customers_router
from app.api.v1.dimensions import router as dimensions_router
from app.api.v1.employees import router as employees_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.journals import router as journals_router
from app.api.v1.journal_lines import router as journal_lines_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.products import router as products_router
from app.api.v1.stock import router as stock_router
from app.api.v1.unit_conversions import router as unit_conversions_router
from app.api.v1.units import router as units_router
from app.api.v1.purchase_invoices import router as purchase_invoices_router
from app.api.v1.roles import router as roles_router
from app.api.v1.sales_invoices import router as sales_invoices_router
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.treasury import router as treasury_router
from app.api.v1.treasury_cash import router as treasury_cash_router
from app.api.v1.vendors import router as vendors_router

_include(accounts_router, prefix="/v1", tags=["accounts"])
_include(customers_router, prefix="/v1", tags=["customers"])
_include(dimensions_router, prefix="/v1", tags=["dimensions"])
_include(employees_router, prefix="/v1", tags=["employees"])
_include(feedback_router, prefix="/v1", tags=["feedback"])
_include(inventory_router, prefix="/v1", tags=["inventory"])
_include(journals_router, prefix="/v1", tags=["journals"])
_include(journal_lines_router, prefix="/v1", tags=["journal_lines"])
_include(notifications_router, prefix="/v1", tags=["notifications"])
_include(products_router, prefix="/v1", tags=["products"])
_include(purchase_invoices_router, prefix="/v1", tags=["purchase_invoices"])
_include(roles_router, prefix="/v1", tags=["roles"])
_include(sales_invoices_router, prefix="/v1", tags=["sales_invoices"])
_include(suppliers_router, prefix="/v1", tags=["suppliers"])
_include(tenants_router, prefix="/v1", tags=["tenants"])
_include(units_router, prefix="/v1", tags=["units"])
_include(unit_conversions_router, prefix="/v1", tags=["unit_conversions"])
_include(stock_router, prefix="/v1", tags=["stock"])
_include(treasury_router, prefix="/v1", tags=["treasury"])
_include(treasury_cash_router, prefix="/v1", tags=["treasury_cash"])
_include(vendors_router, prefix="/v1", tags=["vendors"])

if settings.feature_optional_routes:
    from app.api.v1.admin import router as admin_router
    from app.api.v1.ai import router as ai_router
    from app.api.v1.ai_runs import router as ai_runs_router
    from app.api.v1.auth import router as auth_router
    from app.api.v1.billing import router as billing_router
    from app.api.v1.dashboard import router as dashboard_router
    from app.api.v1.debts import router as debts_router
    from app.api.v1.dev import router as dev_router
    from app.api.v1.expenses import router as expenses_router
    from app.api.v1.gdpr import router as gdpr_router
    from app.api.v1.invoices import router as invoices_router
    from app.api.v1.journal_entries import router as journal_entries_router
    from app.api.v1.ml import router as ml_router
    from app.api.v1.onboarding import router as onboarding_router
    from app.api.v1.payments import router as payments_router
    from app.api.v1.portal import contract_router as portal_contract_router
    from app.api.v1.portal import router as portal_router
    from app.api.v1.recurring_invoices import router as recurring_invoices_router
    from app.api.v1.reports import router as reports_router
    from app.api.v1.settings import router as settings_router
    from app.api.v1.users import router as users_router

    _include(settings_router, prefix="/v1", tags=["settings"])
    _include(dashboard_router, prefix="/v1", tags=["dashboard"])
    _include(portal_contract_router, prefix="", tags=["portal"])
    _include(auth_router, prefix="/v1", tags=["auth"])
    _include(users_router, prefix="/v1", tags=["users"])
    _include(debts_router, prefix="/v1", tags=["debts"])
    _include(invoices_router, prefix="/v1", tags=["invoices"])
    _include(payments_router, prefix="/v1", tags=["payments"])
    _include(expenses_router, prefix="/v1", tags=["expenses"])
    _include(journal_entries_router, prefix="/v1", tags=["journal_entries"])
    _include(billing_router, prefix="/v1", tags=["billing"])
    _include(onboarding_router, prefix="/v1", tags=["onboarding"])
    _include(gdpr_router, prefix="/v1", tags=["gdpr"])
    _include(portal_router, prefix="/v1", tags=["portal"])
    _include(reports_router, prefix="/v1", tags=["reports"])
    _include(ai_router, prefix="/v1", tags=["ai"])
    _include(ai_runs_router, prefix="/v1", tags=["ai"])
    _include(ml_router, prefix="/v1", tags=["ml"])
    _include(dev_router, prefix="/v1", tags=["dev"])
    _include(admin_router, prefix="/v1", tags=["admin"])
    _include(recurring_invoices_router, prefix="/v1", tags=["recurring_invoices"])

__all__ = ["router"]
