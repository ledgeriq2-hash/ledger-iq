from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.rate_limit import enforce_rate_limit
from app.metrics import FEEDBACK_SUBMISSIONS
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackPublic
from app.services import feedback_service, tenant_service

router = APIRouter(prefix="/feedback")


@router.post("/", response_model=FeedbackPublic, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    settings=Depends(deps.get_settings),
):
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant required")
    await enforce_rate_limit(request, "feedback", settings.feedback_rate_limit_per_minute)
    feedback = await feedback_service.create_feedback(
        session,
        tenant_id=tenant_id,
        user_id=current_user.id,
        category=payload.category,
        message=payload.message,
    )
    try:
        tenant = await tenant_service.get_tenant(session, tenant_id, scope_id=None)
        slug = tenant.slug if tenant else ""
        FEEDBACK_SUBMISSIONS.labels(tenant_slug=slug or "unknown").inc()
    except Exception:
        pass
    return feedback


@router.get("/", response_model=FeedbackListResponse)
async def list_my_feedback(
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant required")
    items = await feedback_service.list_feedback(session, tenant_id=tenant_id, limit=50)
    return {"items": items}


__all__ = ["router"]
