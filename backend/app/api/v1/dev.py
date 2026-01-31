from __future__ import annotations

import os
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.initial_data import seed_tenant
from app.models.account import Account
from app.models.tenant import Tenant
from app.models.unit import InventoryUnit
from app.schemas.common import BaseSchema
from app.services import (
    customer_service,
    inventory_unit_service,
    product_service,
    sales_invoice_service,
    vendor_service,
)
from app.use_cases.auth.register import register_tenant_admin

router = APIRouter(prefix="/dev")


class DevInfo(BaseSchema):
    status: str
    environment: str
    tenant_id: UUID


class DevTenantSummary(BaseSchema):
    id: UUID
    name: str
    slug: str


class DevTenantListResponse(BaseSchema):
    items: list[DevTenantSummary]


class BootstrapTenant(BaseSchema):
    name: str | None = None
    slug: str | None = None
    plan: str | None = None
    settings_json: dict | None = None


class BootstrapAdmin(BaseSchema):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None


class BootstrapRequest(BaseSchema):
    tenant: BootstrapTenant | None = None
    admin: BootstrapAdmin | None = None
    seed_demo: bool | None = None


def _ensure_dev(settings) -> None:
    env = str(getattr(settings, "environment", "development") or "development").strip().lower()
    app_env = str(os.getenv("APP_ENV", "")).strip().lower()
    allow_flag = os.getenv("LEDGERIQ_ALLOW_DEV_ENDPOINTS") == "1"
    if env == "development" or app_env == "dev" or allow_flag:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev endpoints are not enabled")


async def _ensure_base_unit(session: AsyncSession, tenant_id: UUID) -> InventoryUnit:
    result = await session.execute(
        select(InventoryUnit)
        .where(InventoryUnit.tenant_id == tenant_id)
        .order_by(InventoryUnit.created_at.asc())
    )
    unit = result.scalars().first()
    if unit:
        return unit
    return await inventory_unit_service.create_unit(
        session,
        tenant_id,
        {
            "code": "EA",
            "name": "Each",
            "ratio_to_base": "1",
        },
    )


async def _ensure_revenue_account(session: AsyncSession, tenant_id: UUID) -> Account:
    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.code == "4000")
    )
    account = result.scalar_one_or_none()
    if account:
        return account
    account = Account(
        tenant_id=tenant_id,
        code="4000",
        name="Sales Revenue",
        type="INCOME",
        normal_balance="credit",
        is_system=True,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def _seed_demo_data(session: AsyncSession, tenant_id: UUID) -> None:
    tenant = await session.get(Tenant, tenant_id)
    if tenant:
        await seed_tenant(session, tenant)

    suffix = uuid4().hex[:6]
    customer = await customer_service.create_customer(
        session,
        tenant_id,
        {
            "name": f"Demo Customer {suffix}",
            "email": f"customer-{suffix}@example.com",
        },
    )
    await vendor_service.create_vendor(
        session,
        tenant_id,
        {
            "name": f"Demo Vendor {suffix}",
            "email": f"vendor-{suffix}@example.com",
        },
    )
    base_unit = await _ensure_base_unit(session, tenant_id)
    product = await product_service.create_product(
        session,
        tenant_id,
        {
            "name": f"Demo Product {suffix}",
            "sku": f"DEMO-{suffix}",
            "unit_price": "100.00",
            "is_service": True,
            "base_unit_id": base_unit.id,
        },
    )
    revenue_account = await _ensure_revenue_account(session, tenant_id)
    invoice_payload = {
        "customer_id": customer.id,
        "invoice_date": date.today(),
        "due_date": date.today(),
        "invoice_no": f"INV-{suffix}",
        "lines": [
            {
                "line_no": 1,
                "description": "Demo line item",
                "quantity": "1",
                "unit_price": "100.00",
                "product_id": product.id,
                "unit_id": base_unit.id,
                "revenue_account_id": revenue_account.id,
                "vat_rate": "0",
            }
        ],
    }
    await sales_invoice_service.create_sales_invoice(session, tenant_id, invoice_payload)


@router.get("/info", response_model=DevInfo)
async def dev_info(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    settings=Depends(deps.get_settings),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = session
    return DevInfo(
        status="ok",
        environment=str(getattr(settings, "environment", "unknown")),
        tenant_id=tenant_id,
    )


@router.get("/tenants", response_model=DevTenantListResponse)
async def list_tenants(
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    _ensure_dev(settings)
    result = await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return DevTenantListResponse(
        items=[
            DevTenantSummary(id=tenant.id, name=tenant.name, slug=tenant.slug)
            for tenant in tenants
        ]
    )


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
async def bootstrap(
    request: Request,
    payload: BootstrapRequest | None = None,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    _ensure_dev(settings)
    seed_demo = bool(payload and payload.seed_demo)
    existing = await session.scalar(select(func.count()).select_from(Tenant))
    if existing and existing > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant already exists")

    suffix = uuid4().hex[:6]
    tenant_payload = payload.tenant if payload and payload.tenant else BootstrapTenant()
    admin_payload = payload.admin if payload and payload.admin else BootstrapAdmin()

    tenant_name = tenant_payload.name or f"Demo Company {suffix}"
    tenant_slug = tenant_payload.slug or f"demo-{suffix}"
    admin_email = admin_payload.email or f"admin-{tenant_slug}@example.com"
    admin_password = admin_payload.password or "Test1234"
    admin_full_name = admin_payload.full_name or "Demo Admin"

    bootstrap_payload = BootstrapRequest(
        tenant=BootstrapTenant(
            name=tenant_name,
            slug=tenant_slug,
            plan=tenant_payload.plan,
            settings_json=tenant_payload.settings_json,
        ),
        admin=BootstrapAdmin(
            email=admin_email,
            password=admin_password,
            full_name=admin_full_name,
        ),
    )

    result = await register_tenant_admin(bootstrap_payload, request, session, settings)
    tenant_id = UUID(str(result["tenant"]["id"]))
    if seed_demo:
        await _seed_demo_data(session, tenant_id)
    tokens = result["tokens"].token.model_dump()
    return {
        "tenant_id": str(tenant_id),
        "admin_email": admin_email,
        "access_token": tokens.get("access_token"),
        "tenant": result["tenant"],
    }


@router.post("/reset-cache", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def reset_cache(
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = tenant_id
    raise AppException(
        code="dev_not_implemented",
        message="Dev utilities are not enabled in this environment.",
        http_status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@router.get("/trigger-500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def trigger_server_error(settings=Depends(deps.get_settings)):
    _ensure_dev(settings)
    raise RuntimeError("triggered")


__all__ = ["router"]
