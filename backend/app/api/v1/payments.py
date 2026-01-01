from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.payment import (
    PaymentAdjustmentCreate,
    PaymentCreate,
    PaymentList,
    PaymentPublic,
    PaymentUpdate,
)
from app.services import payment_service

router = APIRouter(prefix="/payments")


@router.get("/", response_model=PaymentList)
async def list_payments(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    payments, total = await payment_service.list_payments(session, tenant_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if page_size else 0
    return PaymentList(items=payments, page=page, page_size=page_size, total=total, pages=pages)


@router.get("/{payment_id}", response_model=PaymentPublic)
async def get_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    payment = await payment_service.get_payment(session, tenant_id, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("/", response_model=PaymentPublic, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await payment_service.create_payment(session, tenant_id, payload, actor_id=actor_id)


@router.put("/{payment_id}", response_model=PaymentPublic)
async def update_payment(
    payment_id: UUID,
    payload: PaymentUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    payment = await payment_service.update_payment(session, tenant_id, payment_id, payload)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post(
    "/{payment_id}/adjustments",
    response_model=PaymentPublic,
    summary="Create payment adjustment (positive amount only)",
    description=(
        "Adjustment amount must be positive; refunds are not supported. "
        "Adjustments create a separate journal entry and do not change cash unless a treasury movement is recorded separately."
    ),
)
async def create_payment_adjustment(
    payment_id: UUID,
    request: Request,
    payload: PaymentAdjustmentCreate = Body(
        ...,
        description=(
            "Adjustment amount must be positive; refunds are not supported. "
            "Adjustments create a separate journal entry and do not change cash unless a treasury movement is recorded separately."
        ),
    ),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    payment = await payment_service.adjust_payment(
        session,
        tenant_id,
        payment_id,
        payload,
        actor_id=actor_id,
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


__all__ = ["router"]
