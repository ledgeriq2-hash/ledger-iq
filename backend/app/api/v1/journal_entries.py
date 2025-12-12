from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryList,
    JournalEntryPublic,
    JournalEntryUpdate,
)
from app.services import journal_service

router = APIRouter(prefix="/journal-entries")


@router.get("/", response_model=JournalEntryList)
async def list_journal_entries(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    entries = await journal_service.list_journal_entries(session, tenant_id)
    return JournalEntryList(items=entries)


@router.get("/{entry_id}", response_model=JournalEntryPublic)
async def get_journal_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    entry = await journal_service.get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return entry


@router.post("/", response_model=JournalEntryPublic, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    payload: JournalEntryCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    try:
        return await journal_service.create_journal_entry(session, tenant_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{entry_id}", response_model=JournalEntryPublic)
async def update_journal_entry(
    entry_id: UUID,
    payload: JournalEntryUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    try:
        entry = await journal_service.update_journal_entry(session, tenant_id, entry_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await journal_service.delete_journal_entry(session, tenant_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return None


__all__ = ["router"]
