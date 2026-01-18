from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.journal_entry import (
    JournalEntryAdjustmentRequest,
    JournalEntryCreate,
    JournalEntryList,
    JournalEntryPublic,
    JournalEntryReverseRequest,
    JournalEntryUpdate,
    JournalEntryVoidRequest,
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
    current_user: User = Depends(deps.get_current_active_user),
):
    try:
        actor_id = getattr(current_user, "id", None)
        return await journal_service.create_journal_entry(session, tenant_id, payload, actor_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{entry_id}", response_model=JournalEntryPublic)
async def update_journal_entry(
    entry_id: UUID,
    payload: JournalEntryUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: User = Depends(deps.get_current_active_user),
):
    try:
        actor_id = getattr(current_user, "id", None)
        entry = await journal_service.update_journal_entry(
            session,
            tenant_id,
            entry_id,
            payload,
            actor_id=actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return entry


@router.post("/{entry_id}/reverse", response_model=JournalEntryPublic)
async def reverse_journal_entry(
    entry_id: UUID,
    payload: JournalEntryReverseRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: User = Depends(deps.get_current_active_user),
):
    actor_id = getattr(current_user, "id", None)
    return await journal_service.reverse_journal_entry(
        session,
        tenant_id,
        entry_id,
        actor_id=actor_id,
        reason=payload.reason,
    )


@router.post("/{entry_id}/void", response_model=JournalEntryPublic)
async def void_journal_entry(
    entry_id: UUID,
    payload: JournalEntryVoidRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(current_user, "id", None)
    return await journal_service.void_journal_entry(
        session,
        tenant_id,
        entry_id,
        actor_id=actor_id,
        reason=payload.reason,
    )


@router.post("/{entry_id}/adjust", response_model=JournalEntryPublic)
async def adjust_journal_entry(
    entry_id: UUID,
    payload: JournalEntryAdjustmentRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    actor_id = getattr(current_user, "id", None)
    return await journal_service.adjust_journal_entry(
        session,
        tenant_id,
        entry_id,
        actor_id=actor_id,
        reason=payload.reason,
        lines=[line.model_dump() for line in payload.lines],
        idempotency_key=idempotency_key or "",
    )


__all__ = ["router"]
