from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
):
    expenses = await expense_service.list_expenses(session, tenant_id)
    return ExpenseList(items=expenses)


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
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await expense_service.create_expense(session, tenant_id, payload)


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


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await expense_service.delete_expense(session, tenant_id, expense_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return None


__all__ = ["router"]
