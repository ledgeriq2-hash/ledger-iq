from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.customer_receipt import (
    CustomerReceiptAllocationCreate,
    CustomerReceiptAllocationRead,
    CustomerReceiptAllocationUpdate,
    CustomerReceiptRead,
    CustomerReceiptUpdateDraft,
)
from app.schemas.journals import JournalEntryReverseRequest
from app.services import customer_receipt_service

router = APIRouter(prefix="/receipts")


@router.get("/{receipt_id}", response_model=CustomerReceiptRead)
async def get_receipt(
    receipt_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    receipt = await customer_receipt_service.get_receipt(session, tenant_id, receipt_id)
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


@router.put("/{receipt_id}", response_model=CustomerReceiptRead)
async def update_receipt(
    receipt_id: UUID,
    payload: CustomerReceiptUpdateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    receipt = await customer_receipt_service.update_receipt(session, tenant_id, receipt_id, payload)
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


@router.get("/{receipt_id}/allocations", response_model=list[CustomerReceiptAllocationRead])
async def list_receipt_allocations(
    receipt_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await customer_receipt_service.list_receipt_allocations(session, tenant_id, receipt_id)


@router.post("/{receipt_id}/allocations", response_model=CustomerReceiptAllocationRead, status_code=201)
async def add_receipt_allocation(
    receipt_id: UUID,
    payload: CustomerReceiptAllocationCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await customer_receipt_service.add_receipt_allocation(session, tenant_id, receipt_id, payload)


@router.put("/{receipt_id}/allocations/{allocation_id}", response_model=CustomerReceiptAllocationRead)
async def update_receipt_allocation(
    receipt_id: UUID,
    allocation_id: UUID,
    payload: CustomerReceiptAllocationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await customer_receipt_service.update_receipt_allocation(
        session, tenant_id, receipt_id, allocation_id, payload
    )


@router.delete("/{receipt_id}/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt_allocation(
    receipt_id: UUID,
    allocation_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await customer_receipt_service.delete_receipt_allocation(
        session, tenant_id, receipt_id, allocation_id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt allocation not found")
    return None


@router.post("/{receipt_id}/post", response_model=CustomerReceiptRead)
async def post_receipt(
    receipt_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await customer_receipt_service.post_receipt(session, tenant_id, receipt_id, actor_id=actor_id)


@router.post("/{receipt_id}/reverse", response_model=CustomerReceiptRead)
async def reverse_receipt(
    receipt_id: UUID,
    payload: JournalEntryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await customer_receipt_service.reverse_receipt(
        session,
        tenant_id,
        receipt_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
