from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.services import customer_service, invoice_service, payment_service, product_service


def _ensure_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


async def _get_tenant_settings(session: AsyncSession, tenant_id: UUID) -> tuple[Tenant, dict]:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    settings = _ensure_dict(tenant.settings_json)
    return tenant, settings


async def get_status(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    _, settings = await _get_tenant_settings(session, tenant_id)
    onboarding = _ensure_dict(settings.get("onboarding"))
    accounting = _ensure_dict(settings.get("accounting"))
    branding = _ensure_dict(settings.get("branding"))
    return {
        "step": onboarding.get("step", "profile"),
        "profile_completed": bool(onboarding.get("profile_completed")),
        "sample_data_loaded": bool(onboarding.get("sample_data_loaded")),
        "logo_url": branding.get("logo_url"),
        "currency": accounting.get("currency", "USD"),
        "fiscal_year_start": accounting.get("fiscal_year_start", "01-01"),
        "chart_preset": accounting.get("chart_preset", "basic"),
    }


async def update_status(
    session: AsyncSession,
    tenant_id: UUID,
    data: dict[str, Any],
) -> dict[str, Any]:
    tenant, settings = await _get_tenant_settings(session, tenant_id)
    onboarding = _ensure_dict(settings.get("onboarding"))
    accounting = _ensure_dict(settings.get("accounting"))
    branding = _ensure_dict(settings.get("branding"))

    for field in ("step", "profile_completed", "sample_data_loaded"):
        if field in data:
            onboarding[field] = data[field]
    if "logo_url" in data:
        branding["logo_url"] = data["logo_url"]
    if "currency" in data:
        accounting["currency"] = data["currency"]
    if "fiscal_year_start" in data:
        accounting["fiscal_year_start"] = data["fiscal_year_start"]
    if "chart_preset" in data:
        accounting["chart_preset"] = data["chart_preset"]

    settings["onboarding"] = onboarding
    settings["accounting"] = accounting
    settings["branding"] = branding
    tenant.settings_json = settings
    await session.commit()
    return await get_status(session, tenant_id)


async def create_sample_data(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    status = await get_status(session, tenant_id)
    if status.get("sample_data_loaded"):
        return status

    customer = await customer_service.create_customer(
        session,
        tenant_id,
        {"code": "SAMPLE", "name": "Sample Customer", "email": "sample@ledger.test", "phone": "555-0101"},
    )
    product = await product_service.create_product(
        session,
        tenant_id,
        {"name": "Starter Package", "sku": "START-01", "unit_price": "199.00", "is_service": True},
    )
    today = date.today()
    invoice = await invoice_service.create_invoice(
        session,
        tenant_id,
        {
            "customer_id": customer.id,
            "issue_date": today.isoformat(),
            "due_date": today.isoformat(),
            "status": "PAID",
            "currency": status.get("currency", "USD"),
            "items": [
                {"product_id": product.id, "description": "Sample setup", "quantity": "1", "unit_price": "199.00"}
            ],
        },
    )
    await payment_service.create_payment(
        session,
        tenant_id,
        {"invoice_id": invoice.id, "customer_id": customer.id, "amount": invoice.total_amount, "method": "card"},
    )

    updated = await update_status(session, tenant_id, {"sample_data_loaded": True})
    return updated


__all__ = ["get_status", "update_status", "create_sample_data"]
