from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import require_perm
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.schemas.accounts import (
    AccountCreate,
    AccountList,
    AccountMappingCreate,
    AccountMappingList,
    AccountMappingPublic,
    AccountPublic,
    AccountUpdate,
)

router = APIRouter(prefix="/accounts")


@router.get("/", response_model=AccountList)
async def list_accounts(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.view")),
):
    stmt = select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code)
    result = await session.execute(stmt)
    return AccountList(items=result.scalars().all())


@router.post("/", response_model=AccountPublic, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.manage")),
):
    parent_id = payload.parent_id
    if parent_id:
        parent = await session.get(Account, parent_id)
        if not parent or parent.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent account not found")

    account = Account(
        tenant_id=tenant_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        type=payload.type.strip(),
        normal_balance=payload.normal_balance.strip(),
        parent_id=parent_id,
        is_system=False,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountPublic)
async def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.manage")),
):
    account = await session.get(Account, account_id)
    if not account or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if account.is_system:
        raise AppException(
            code="system_account_locked",
            message="System accounts cannot be edited",
            http_status=409,
        )

    if payload.name is not None:
        account.name = payload.name.strip()
    if payload.type is not None:
        account.type = payload.type.strip()
    if payload.normal_balance is not None:
        account.normal_balance = payload.normal_balance.strip()
    if payload.parent_id is not None:
        if payload.parent_id:
            parent = await session.get(Account, payload.parent_id)
            if not parent or parent.tenant_id != tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent account not found")
        account.parent_id = payload.parent_id
    if payload.is_active is not None:
        account.is_active = payload.is_active

    await session.commit()
    await session.refresh(account)
    return account


@router.post("/{account_id}/deactivate", response_model=AccountPublic)
async def deactivate_account(
    account_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.manage")),
):
    account = await session.get(Account, account_id)
    if not account or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if account.is_system:
        raise AppException(
            code="system_account_locked",
            message="System accounts cannot be deactivated",
            http_status=409,
        )

    account.is_active = False
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/mappings", response_model=AccountMappingList)
async def list_mappings(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.view")),
):
    stmt = select(AccountMapping).where(AccountMapping.tenant_id == tenant_id).order_by(AccountMapping.key)
    result = await session.execute(stmt)
    return AccountMappingList(items=result.scalars().all())


@router.post("/mappings", response_model=AccountMappingPublic, status_code=status.HTTP_201_CREATED)
async def upsert_mapping(
    payload: AccountMappingCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("coa.manage")),
):
    account = await session.get(Account, payload.account_id)
    if not account or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    mapping_key = payload.key.strip()
    stmt = select(AccountMapping).where(
        AccountMapping.tenant_id == tenant_id,
        AccountMapping.key == mapping_key,
    )
    result = await session.execute(stmt)
    mapping = result.scalar_one_or_none()
    if mapping:
        mapping.account_id = payload.account_id
        await session.commit()
        await session.refresh(mapping)
        return mapping

    mapping = AccountMapping(
        tenant_id=tenant_id,
        key=mapping_key,
        account_id=payload.account_id,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


__all__ = ["router"]
