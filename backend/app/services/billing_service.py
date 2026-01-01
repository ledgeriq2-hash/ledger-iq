from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException
from app.models.ai_log import AiLog
from app.models.attachment import Attachment
from app.models.billing_plan import BillingPlan
from app.models.invoice import Invoice
from app.models.stripe_event import StripeEvent
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.services import stripe_service


_get_stripe = stripe_service.get_stripe_client


async def ensure_default_plans(session: AsyncSession, settings=None) -> None:
    settings = settings or get_settings()
    defaults: list[dict[str, Any]] = [
        {
            "code": settings.default_plan_code or "free",
            "name": "Free",
            "price_cents": 0,
            "currency": "usd",
            "interval": "month",
            "limits_json": {"users": 3, "invoices": 50, "storage_mb": 512, "ai_calls": 50},
            "metadata_json": {"stripe_price_id": getattr(settings, "stripe_price_free", None)},
        },
        {
            "code": "pro",
            "name": "Pro",
            "price_cents": 4900,
            "currency": "usd",
            "interval": "month",
            "limits_json": {"users": 25, "invoices": 5000, "storage_mb": 20480, "ai_calls": 2000},
            "metadata_json": {"stripe_price_id": getattr(settings, "stripe_price_pro", None)},
        },
    ]
    existing = {
        plan.code
        for plan in (await session.execute(select(BillingPlan.code))).scalars().all()
    }
    created = []
    for payload in defaults:
        if payload["code"] in existing:
            continue
        plan = BillingPlan(**payload)
        session.add(plan)
        created.append(plan)
    if created:
        await session.commit()
        for plan in created:
            await session.refresh(plan)


async def list_plans(session: AsyncSession) -> list[BillingPlan]:
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.price_cents.asc()))
    return result.scalars().all()


async def get_plan(session: AsyncSession, code: str | None) -> BillingPlan | None:
    if not code:
        return None
    result = await session.execute(select(BillingPlan).where(BillingPlan.code == code))
    return result.scalar_one_or_none()


async def _get_or_create_subscription(session: AsyncSession, tenant_id: UUID, settings=None) -> TenantSubscription:
    settings = settings or get_settings()
    result = await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id))
    subscription = result.scalar_one_or_none()
    if subscription:
        return subscription
    subscription = TenantSubscription(
        tenant_id=tenant_id,
        status="active",
        plan_code=getattr(settings, "default_plan_code", None),
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def _sync_tenant_plan(session: AsyncSession, tenant_id: UUID, plan_code: str | None) -> None:
    if not plan_code:
        return
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant and tenant.plan != plan_code:
        tenant.plan = plan_code
        await session.commit()


async def get_usage_snapshot(session: AsyncSession, tenant_id: UUID) -> dict[str, float]:
    users = await session.scalar(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
    ) or 0
    invoices = await session.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id)
    ) or 0
    start_month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ai_calls = await session.scalar(
        select(func.count()).select_from(AiLog).where(AiLog.tenant_id == tenant_id, AiLog.created_at >= start_month)
    ) or 0
    attachments_bytes = await session.scalar(
        select(func.coalesce(func.sum(Attachment.size), 0)).where(Attachment.tenant_id == tenant_id)
    ) or 0
    ai_payload_bytes = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(func.length(AiLog.input_data), 0) + func.coalesce(func.length(AiLog.output_data), 0)
                ),
                0,
            )
        ).where(AiLog.tenant_id == tenant_id)
    ) or 0
    storage_bytes = attachments_bytes + ai_payload_bytes
    storage_mb = float(storage_bytes) / (1024 * 1024) if storage_bytes else 0.0
    return {
        "users": int(users),
        "invoices": int(invoices),
        "ai_calls": int(ai_calls),
        "storage_mb": round(storage_mb, 2),
    }


async def get_subscription_status(session: AsyncSession, tenant_id: UUID, settings=None) -> dict[str, Any]:
    settings = settings or get_settings()
    subscription = await _get_or_create_subscription(session, tenant_id)
    plan_code = subscription.plan_code
    if not plan_code:
        result = await session.execute(select(Tenant.plan).where(Tenant.id == tenant_id))
        plan_code = result.scalar_one_or_none() or settings.default_plan_code
    plan = await get_plan(session, plan_code)
    usage = await get_usage_snapshot(session, tenant_id)
    limits = plan.limits_json if plan else None
    return {
        "plan": plan,
        "plan_code": plan.code if plan else plan_code,
        "subscription": subscription,
        "usage": usage,
        "limits": limits or {},
    }


async def enforce_plan_limit(session: AsyncSession, tenant_id: UUID, metric: str, increment: float = 1) -> None:
    status_payload = await get_subscription_status(session, tenant_id)
    limits = status_payload.get("limits") or {}
    limit_value = limits.get(metric)
    if not limit_value:
        return
    plan = status_payload.get("plan")
    subscription = status_payload.get("subscription")
    if plan and (plan.price_cents or 0) > 0:
        status_value = getattr(subscription, "status", None)
        if status_value not in {"active", "trialing"}:
            raise AppException(
                code="subscription_required",
                message="Active subscription required",
                http_status=status.HTTP_402_PAYMENT_REQUIRED,
            )
    usage = status_payload.get("usage", {})
    current_value = float(usage.get(metric) or 0)
    if current_value + increment > float(limit_value):
        plan_name = status_payload.get("plan").name if status_payload.get("plan") else status_payload.get("plan_code")
        raise AppException(
            code=f"{metric}_limit_reached",
            message=f"{metric.replace('_', ' ').title()} limit reached for plan {plan_name}",
            http_status=status.HTTP_402_PAYMENT_REQUIRED,
        )


def _extract_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except Exception:
        return None


async def create_checkout_session(
    session: AsyncSession,
    tenant_id: UUID,
    plan_code: str,
    success_url: str,
    cancel_url: str,
    settings=None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    plan = await get_plan(session, plan_code)
    if not plan:
        raise AppException("plan_not_found", "Plan not found", http_status=status.HTTP_404_NOT_FOUND)

    subscription = await _get_or_create_subscription(session, tenant_id, settings=settings)
    stripe_client = _get_stripe(settings)
    if not stripe_client:
        raise AppException("stripe_not_configured", "Stripe API key is not configured", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    price_id = (plan.metadata_json or {}).get("stripe_price_id")
    if not price_id:
        raise AppException("plan_price_missing", "Plan missing Stripe price id")

    customer_id = subscription.stripe_customer_id
    if not customer_id:
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        customer = stripe_client.Customer.create(
            name=tenant.name if tenant else str(tenant_id),
            metadata={"tenant_id": str(tenant_id)},
        )
        customer_id = customer.id
        subscription.stripe_customer_id = customer_id
        await session.commit()

    checkout = stripe_client.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": str(tenant_id), "plan_code": plan.code},
        subscription_data={"metadata": {"tenant_id": str(tenant_id), "plan_code": plan.code}},
    )
    subscription.plan_code = plan.code
    subscription.checkout_session_id = checkout.id
    subscription.status = "pending"
    await session.commit()
    await _sync_tenant_plan(session, tenant_id, plan.code)
    return {"url": checkout.url, "id": checkout.id}


async def create_customer_portal_session(
    session: AsyncSession, tenant_id: UUID, return_url: str, settings=None
) -> dict[str, str]:
    settings = settings or get_settings()
    stripe_client = _get_stripe(settings)
    if not stripe_client:
        raise AppException("stripe_not_configured", "Stripe API key is not configured", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    subscription = await _get_or_create_subscription(session, tenant_id, settings=settings)
    customer_id = subscription.stripe_customer_id
    if not customer_id:
        raise AppException("missing_customer", "No Stripe customer for tenant", http_status=status.HTTP_404_NOT_FOUND)

    portal_session = stripe_client.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return {"url": portal_session.url}


async def handle_webhook_event(session: AsyncSession, payload: bytes, signature: str | None, settings=None) -> dict:
    settings = settings or get_settings()
    event, idempotent, event_type = await stripe_service.verify_and_record_webhook(
        session, payload, signature, settings=settings
    )
    if idempotent:
        return {"received": True, "event_type": event_type, "idempotent": True}
    if not event:
        return {"received": True, "event_type": event_type, "idempotent": True}

    data_object = (event.get("data") or {}).get("object") or {}

    tenant_id = data_object.get("metadata", {}).get("tenant_id") or data_object.get("tenant_id")
    plan_code = data_object.get("metadata", {}).get("plan_code")
    try:
        tenant_uuid = UUID(str(tenant_id)) if tenant_id else None
    except Exception:
        tenant_uuid = None

    if tenant_uuid is None:
        customer_id = data_object.get("customer")
        if customer_id:
            result = await session.execute(
                select(TenantSubscription).where(TenantSubscription.stripe_customer_id == customer_id)
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                tenant_uuid = subscription.tenant_id
                if not plan_code:
                    plan_code = subscription.plan_code

    if event_type == "checkout.session.completed" and tenant_uuid:
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        subscription = await _get_or_create_subscription(session, tenant_uuid, settings=settings)
        subscription.plan_code = plan_code or subscription.plan_code
        subscription.status = "active"
        subscription.stripe_customer_id = customer_id or subscription.stripe_customer_id
        subscription.stripe_subscription_id = subscription_id or subscription.stripe_subscription_id
        subscription.checkout_session_id = data_object.get("id") or subscription.checkout_session_id
        await session.commit()
        await _sync_tenant_plan(session, tenant_uuid, subscription.plan_code)
    elif event_type == "invoice.payment_failed" and tenant_uuid:
        subscription = await _get_or_create_subscription(session, tenant_uuid, settings=settings)
        subscription.status = "past_due"
        await session.commit()
    elif event_type == "customer.subscription.deleted" and tenant_uuid:
        subscription = await _get_or_create_subscription(session, tenant_uuid, settings=settings)
        subscription.status = "canceled"
        subscription.cancel_at_period_end = True
        await session.commit()
        await _sync_tenant_plan(session, tenant_uuid, subscription.plan_code)
    elif event_type and event_type.startswith("customer.subscription") and tenant_uuid:
        subscription = await _get_or_create_subscription(session, tenant_uuid, settings=settings)
        subscription.plan_code = plan_code or subscription.plan_code
        subscription.status = data_object.get("status") or subscription.status
        subscription.stripe_subscription_id = data_object.get("id") or subscription.stripe_subscription_id
        subscription.current_period_end = _extract_timestamp(data_object.get("current_period_end"))
        subscription.cancel_at_period_end = bool(data_object.get("cancel_at_period_end"))
        await session.commit()
        await _sync_tenant_plan(session, tenant_uuid, subscription.plan_code)

    return {"received": True, "event_type": event_type}


__all__ = [
    "ensure_default_plans",
    "list_plans",
    "get_plan",
    "get_subscription_status",
    "enforce_plan_limit",
    "create_checkout_session",
    "handle_webhook_event",
    "get_usage_snapshot",
]
