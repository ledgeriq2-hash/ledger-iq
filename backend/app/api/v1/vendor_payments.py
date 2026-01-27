from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.journals import JournalEntryReverseRequest
from app.schemas.vendor_payment import (
    VendorPaymentAllocationCreate,
    VendorPaymentAllocationRead,
    VendorPaymentAllocationUpdate,
    VendorPaymentRead,
    VendorPaymentUpdateDraft,
)
from app.services import vendor_payment_service

router = APIRouter(prefix="/payments")


@router.get("/{payment_id}", response_model=VendorPaymentRead)
async def get_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    payment = await vendor_payment_service.get_payment(session, tenant_id, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.put("/{payment_id}", response_model=VendorPaymentRead)
async def update_payment(
    payment_id: UUID,
    payload: VendorPaymentUpdateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    payment = await vendor_payment_service.update_payment(session, tenant_id, payment_id, payload)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.get("/{payment_id}/allocations", response_model=list[VendorPaymentAllocationRead])
async def list_payment_allocations(
    payment_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await vendor_payment_service.list_payment_allocations(session, tenant_id, payment_id)


@router.post("/{payment_id}/allocations", response_model=VendorPaymentAllocationRead, status_code=201)
async def add_payment_allocation(
    payment_id: UUID,
    payload: VendorPaymentAllocationCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await vendor_payment_service.add_payment_allocation(session, tenant_id, payment_id, payload)


@router.put("/{payment_id}/allocations/{allocation_id}", response_model=VendorPaymentAllocationRead)
async def update_payment_allocation(
    payment_id: UUID,
    allocation_id: UUID,
    payload: VendorPaymentAllocationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await vendor_payment_service.update_payment_allocation(
        session, tenant_id, payment_id, allocation_id, payload
    )


@router.delete("/{payment_id}/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_allocation(
    payment_id: UUID,
    allocation_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await vendor_payment_service.delete_payment_allocation(
        session, tenant_id, payment_id, allocation_id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment allocation not found")
    return None


@router.post("/{payment_id}/post", response_model=VendorPaymentRead)
async def post_payment(
    payment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await vendor_payment_service.post_payment(session, tenant_id, payment_id, actor_id=actor_id)


@router.post("/{payment_id}/reverse", response_model=VendorPaymentRead)
async def reverse_payment(
    payment_id: UUID,
    payload: JournalEntryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await vendor_payment_service.reverse_payment(
        session,
        tenant_id,
        payment_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
