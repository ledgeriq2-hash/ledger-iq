from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseList, ExpensePublic, ExpenseUpdate
from app.services import expense_service

router = APIRouter(prefix="/expenses")


@router.get("/", response_model=ExpenseList)
async def list_expenses(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    expenses, total = await expense_service.list_expenses(session, tenant_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if page_size else 0
    return ExpenseList(items=expenses, page=page, page_size=page_size, total=total, pages=pages)


@router.get("/{expense_id}", response_model=ExpensePublic)
async def get_expense(
    expense_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    expense = await expense_service.get_expense(session, tenant_id, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.post("/", response_model=ExpensePublic, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await expense_service.create_expense(session, tenant_id, payload, actor_id=actor_id)


@router.put("/{expense_id}", response_model=ExpensePublic)
async def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    expense = await expense_service.update_expense(session, tenant_id, expense_id, payload)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.post("/{expense_id}/adjustments", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_expense_adjustment(
    expense_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    _ = session, tenant_id, expense_id
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Expense adjustments not implemented yet")


__all__ = ["router"]
