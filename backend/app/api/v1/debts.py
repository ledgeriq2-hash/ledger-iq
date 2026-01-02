from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/debts")


class DebtStub(BaseSchema):
    id: UUID | None = None
    status: str = "not_implemented"
    message: str = "Debt management is not enabled yet."


class DebtList(BaseSchema):
    items: list[DebtStub]
    total: int


def _raise_not_implemented() -> None:
    raise AppException(
        code="debts_not_implemented",
        message="Debt management is not enabled yet.",
        http_status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@router.get("/", response_model=DebtList)
async def list_debts(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = session, tenant_id
    return DebtList(items=[], total=0)


@router.get("/{debt_id}", response_model=DebtStub)
async def get_debt(
    debt_id: UUID,
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = debt_id, tenant_id
    _raise_not_implemented()


@router.post("/", response_model=DebtStub, status_code=status.HTTP_201_CREATED)
async def create_debt(
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = tenant_id
    _raise_not_implemented()


@router.put("/{debt_id}", response_model=DebtStub)
async def update_debt(
    debt_id: UUID,
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = debt_id, tenant_id
    _raise_not_implemented()


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(
    debt_id: UUID,
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = debt_id, tenant_id
    _raise_not_implemented()


__all__ = ["router"]
