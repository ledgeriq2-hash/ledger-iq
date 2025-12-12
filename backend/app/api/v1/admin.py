from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.core.soft_launch import is_soft_launch_tenant
from app.metrics import ADMIN_ACTIONS
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.admin import TenantAdminSummary, TenantOverviewResponse
from app.schemas.error_event import ErrorEventsResponse
from app.schemas.feedback import FeedbackListResponse
from app.schemas.usage import TenantUsageResponse
from app.services import (
    error_event_service,
    feedback_service,
    billing_service,
    tenant_config_service,
    usage_service,
)

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)


def _ensure_same_tenant_or_superuser(current_user: User, tenant_id: UUID) -> None:
    if current_user.is_superuser:
        return
    if not current_user.tenant_id or current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")


async def _get_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


async def _get_owner_email(session: AsyncSession, tenant_id: UUID) -> str | None:
    result = await session.execute(
        select(User.email)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.asc())
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


@router.get("/tenants/", response_model=list[TenantAdminSummary])
async def list_tenants(
    session: AsyncSession = Depends(deps.get_db),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    result = await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    summaries: list[TenantAdminSummary] = []
    for tenant in tenants:
        owner_email = await _get_owner_email(session, tenant.id)
        billing = await billing_service.get_subscription_status(session, tenant.id)
        summaries.append(
            TenantAdminSummary(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                created_at=tenant.created_at,
                owner_email=owner_email,
                is_soft_launch=is_soft_launch_tenant(tenant.slug),
                plan_code=billing.get("plan_code"),
                subscription_status=getattr(billing.get("subscription"), "status", None),
            )
        )
    return summaries


@router.post("/tenants/{tenant_id}/soft-launch/enable")
async def enable_soft_launch(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    tenant = await _get_tenant(session, tenant_id)
    await tenant_config_service.set_soft_launch(session, tenant_id, True)
    try:
        ADMIN_ACTIONS.labels(action="soft_launch_enable").inc()
    except Exception:
        pass
    logger.info("soft_launch.enable", extra={"tenant_id": tenant_id, "slug": tenant.slug, "actor": current_user.id})
    return {"tenant_id": tenant_id, "slug": tenant.slug, "is_soft_launch": True}


@router.post("/tenants/{tenant_id}/soft-launch/disable")
async def disable_soft_launch(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    tenant = await _get_tenant(session, tenant_id)
    await tenant_config_service.set_soft_launch(session, tenant_id, False)
    try:
        ADMIN_ACTIONS.labels(action="soft_launch_disable").inc()
    except Exception:
        pass
    logger.info("soft_launch.disable", extra={"tenant_id": tenant_id, "slug": tenant.slug, "actor": current_user.id})
    return {"tenant_id": tenant_id, "slug": tenant.slug, "is_soft_launch": False}


@router.get("/tenants/{tenant_id}/overview", response_model=TenantOverviewResponse)
async def tenant_overview(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    _ensure_same_tenant_or_superuser(current_user, tenant_id)
    tenant = await _get_tenant(session, tenant_id)
    usage = await usage_service.fetch_recent_usage(session, tenant_id, days=30)
    errors = await error_event_service.fetch_errors_for_tenant(session, tenant_id, limit=20)
    feedback = await feedback_service.list_feedback(session, tenant_id=tenant_id, limit=20)
    billing_info = await billing_service.get_subscription_status(session, tenant_id)

    invoice_count = await session.scalar(select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id))
    payment_count = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.tenant_id == tenant_id)
    )
    last_login = await session.scalar(
        select(func.max(User.last_login_at)).where(User.tenant_id == tenant_id)
    )
    owner_email = await _get_owner_email(session, tenant_id)

    tenant_summary = TenantAdminSummary(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        created_at=tenant.created_at,
        owner_email=owner_email,
        is_soft_launch=is_soft_launch_tenant(tenant.slug),
        plan_code=billing_info.get("plan_code"),
        subscription_status=getattr(billing_info.get("subscription"), "status", None),
    )
    totals = {"invoices": invoice_count or 0, "payments": payment_count or 0}
    return {
        "tenant": tenant_summary,
        "usage": usage,
        "errors": errors,
        "feedback": feedback,
        "totals": totals,
        "last_login_at": last_login,
        "billing": {
            "plan": billing_info.get("plan"),
            "plan_code": billing_info.get("plan_code"),
            "subscription": billing_info.get("subscription"),
            "usage": billing_info.get("usage"),
            "limits": billing_info.get("limits"),
        },
    }


@router.get("/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
async def tenant_usage(
    tenant_id: UUID,
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    _ensure_same_tenant_or_superuser(current_user, tenant_id)
    usage = await usage_service.fetch_recent_usage(session, tenant_id, days=days)
    return {"tenant_id": tenant_id, "usage": usage}


@router.get("/tenants/{tenant_id}/errors", response_model=ErrorEventsResponse)
async def tenant_errors(
    tenant_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    _ensure_same_tenant_or_superuser(current_user, tenant_id)
    items = await error_event_service.fetch_errors_for_tenant(session, tenant_id, limit=limit)
    return {"items": items}


@router.get("/errors/recent", response_model=ErrorEventsResponse)
async def recent_errors(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(deps.get_db),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    items = await error_event_service.fetch_recent_errors(session, limit=limit)
    return {"items": items}


@router.get("/feedback", response_model=FeedbackListResponse)
async def admin_feedback(
    tenant_id: UUID | None = None,
    category: str | None = Query(None, pattern="^(bug|idea|confusion|other)?$"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(deps.get_db),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    items = await feedback_service.list_feedback(session, tenant_id=tenant_id, category=category, limit=limit)
    return {"items": items}


@router.get("/tenants/{tenant_id}/feedback", response_model=FeedbackListResponse)
async def tenant_feedback(
    tenant_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    _ensure_same_tenant_or_superuser(current_user, tenant_id)
    items = await feedback_service.list_feedback(session, tenant_id=tenant_id, limit=limit)
    return {"items": items}


__all__ = ["router"]
