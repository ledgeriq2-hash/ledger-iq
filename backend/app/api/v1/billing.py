from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.billing import BillingOverviewResponse, BillingStatus, PlanPublic
from app.schemas.common import BaseSchema
from app.services import billing_service

router = APIRouter(prefix="/billing")


class CheckoutRequest(BaseSchema):
    plan_code: str
    success_url: str | None = None
    cancel_url: str | None = None


@router.get("/plans", response_model=list[PlanPublic])
async def list_plans(
    session: AsyncSession = Depends(deps.get_db),
    _: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
):
    await billing_service.ensure_default_plans(session)
    return await billing_service.list_plans(session)


@router.get("/subscription", response_model=BillingStatus)
async def subscription_status(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
):
    status_payload = await billing_service.get_subscription_status(session, tenant_id)
    return BillingStatus(**status_payload)


@router.get("/overview", response_model=BillingOverviewResponse)
async def billing_overview(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
    settings=Depends(deps.get_settings),
):
    status_payload = await billing_service.get_subscription_status(session, tenant_id, settings=settings)
    plan = status_payload.get("plan")
    limits = status_payload.get("limits") or {}
    usage = status_payload.get("usage") or {}
    subscription = status_payload.get("subscription")

    plan_info = {
        "plan_code": plan.code if plan else status_payload.get("plan_code"),
        "plan_name": plan.name if plan else status_payload.get("plan_code"),
        "price": (plan.price_cents / 100) if plan and plan.price_cents is not None else None,
        "currency": plan.currency if plan else None,
        "billing_period": plan.interval if plan else None,
    }

    usage_payload = {
        "invoices_this_month": int(usage.get("invoices") or 0),
        "ai_calls_this_month": int(usage.get("ai_calls") or 0),
        "storage_usage_mb": float(usage.get("storage_mb") or 0.0),
    }
    limits_payload = {
        "max_invoices_per_month": limits.get("invoices"),
        "max_ai_calls_per_month": limits.get("ai_calls"),
        "max_storage_mb": limits.get("storage_mb"),
    }

    return BillingOverviewResponse(
        plan=plan_info,
        usage=usage_payload,
        limits=limits_payload,
        stripe_customer_portal_url=None,
        checkout_url=None,
        metadata={"subscription_status": getattr(subscription, "status", None)},
    )


@router.post("/checkout")
async def start_checkout(
    payload: CheckoutRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
    ___ = Depends(require_roles([OWNER, ADMIN])),
    settings=Depends(deps.get_settings),
):
    await billing_service.ensure_default_plans(session, settings)
    success_url = payload.success_url or f"{settings.frontend_url}/billing?status=success"
    cancel_url = payload.cancel_url or f"{settings.frontend_url}/billing?status=cancelled"
    try:
        checkout = await billing_service.create_checkout_session(
            session,
            tenant_id,
            payload.plan_code,
            success_url,
            cancel_url,
            settings,
        )
    except AppException as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    return checkout


@router.post("/portal")
async def create_portal(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
    ___ = Depends(require_roles([OWNER, ADMIN])),
    settings=Depends(deps.get_settings),
):
    try:
        portal = await billing_service.create_customer_portal_session(
            session=session,
            tenant_id=tenant_id,
            return_url=f"{settings.frontend_url}/billing",
            settings=settings,
        )
    except AppException as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    return portal


@router.post("/webhook", include_in_schema=False)
async def billing_webhook(
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    body = await request.body()
    return await billing_service.handle_webhook_event(session, body, stripe_signature)


__all__ = ["router"]
