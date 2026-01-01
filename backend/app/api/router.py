from __future__ import annotations

import logging
from importlib import import_module

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _try_router(module_path: str, *, attr: str = "router"):
    try:
        module = import_module(module_path)
    except Exception as exc:
        logger.warning(
            "router.skip",
            extra={"module_path": module_path, "reason": str(exc)},
        )
        return None
    router_obj = getattr(module, attr, None)
    if router_obj is None:
        logger.warning(
            "router.missing",
            extra={"module_path": module_path, "attr": attr},
        )
    return router_obj


ROUTES = [
    ("app.api.settings", "", ["settings"], "router"),
    ("app.api.v1.dashboard", "/v1", ["dashboard"], "router"),
    ("app.api.v1.portal", "", ["portal"], "contract_router"),
    ("app.api.v1.auth", "/v1", ["auth"], "router"),
    ("app.api.v1.users", "/v1", ["users"], "router"),
    ("app.api.v1.roles", "/v1", ["roles"], "router"),
    ("app.api.v1.tenants", "/v1", ["tenants"], "router"),
    ("app.api.v1.customers", "/v1", ["customers"], "router"),
    ("app.api.v1.suppliers", "/v1", ["suppliers"], "router"),
    ("app.api.v1.debts", "/v1", ["debts"], "router"),
    ("app.api.v1.employees", "/v1", ["employees"], "router"),
    ("app.api.v1.products", "/v1", ["products"], "router"),
    ("app.api.v1.invoices", "/v1", ["invoices"], "router"),
    ("app.api.v1.payments", "/v1", ["payments"], "router"),
    ("app.api.v1.expenses", "/v1", ["expenses"], "router"),
    ("app.api.v1.journal_entries", "/v1", ["journal_entries"], "router"),
    ("app.api.v1.treasury", "/v1", ["treasury"], "router"),
    ("app.api.v1.accounting_periods", "/v1", ["accounting_periods"], "router"),
    ("app.api.v1.billing", "/v1", ["billing"], "router"),
    ("app.api.v1.onboarding", "/v1", ["onboarding"], "router"),
    ("app.api.v1.gdpr", "/v1", ["gdpr"], "router"),
    ("app.api.v1.notifications", "/v1", ["notifications"], "router"),
    ("app.api.v1.portal", "/v1", ["portal"], "router"),
    ("app.api.v1.reports", "/v1", ["reports"], "router"),
    ("app.api.v1.ai", "/v1", ["ai"], "router"),
    ("app.api.v1.ml", "/v1", ["ml"], "router"),
    ("app.api.v1.dev", "/v1", ["dev"], "router"),
    ("app.api.v1.admin", "/v1", ["admin"], "router"),
    ("app.api.v1.feedback", "/v1", ["feedback"], "router"),
    ("app.api.v1.recurring_invoices", "/v1", ["recurring_invoices"], "router"),
    ("app.api.v1.inventory", "/v1", ["inventory"], "router"),
]

for module_path, prefix, tags, attr in ROUTES:
    router_obj = _try_router(module_path, attr=attr)
    if router_obj is None:
        continue
    if prefix:
        router.include_router(router_obj, prefix=prefix, tags=tags)
    else:
        router.include_router(router_obj, tags=tags)

__all__ = ["router"]
