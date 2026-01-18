from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.accounting.use_cases.lock_accounting_period import lock_accounting_period, unlock_accounting_period
from app.core.permissions import require_perm
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.schemas.journals import (
    JournalEntryDetail,
    JournalEntryList,
    JournalEntryManualCreate,
    JournalEntryReverseRequest,
)
from app.schemas.period_lock import AccountingPeriodLockCreate, AccountingPeriodLockPublic
from app.services.ledger_service import LedgerService

router = APIRouter(prefix="/journals")


@router.get("/", response_model=JournalEntryList)
async def list_journals(
    status_filter: list[str] | None = Query(None, alias="status"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    source_type: str | None = Query(None),
    period_year: int | None = Query(None),
    period_month: int | None = Query(None),
    account_id: UUID | None = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("journal.view")),
):
    stmt = select(JournalEntry).where(JournalEntry.tenant_id == tenant_id)

    if status_filter:
        normalized_status = [value.strip().title() for value in status_filter if value and value.strip()]
        if normalized_status:
            stmt = stmt.where(JournalEntry.status.in_(normalized_status))

    if start_date:
        stmt = stmt.where(JournalEntry.entry_date >= start_date)
    if end_date:
        stmt = stmt.where(JournalEntry.entry_date <= end_date)
    if source_type:
        stmt = stmt.where(JournalEntry.source_type == source_type.strip())
    if period_year:
        stmt = stmt.where(JournalEntry.period_year == period_year)
    if period_month:
        stmt = stmt.where(JournalEntry.period_month == period_month)
    if account_id:
        stmt = stmt.join(JournalLine, JournalLine.entry_id == JournalEntry.id).where(
            JournalLine.account_id == account_id
        )

    stmt = stmt.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
    result = await session.execute(stmt)
    entries = result.scalars().unique().all()
    return JournalEntryList(items=entries)


@router.get("/{entry_id}", response_model=JournalEntryDetail)
async def get_journal_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("journal.view")),
):
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
        .options(selectinload(JournalEntry.ledger_lines))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return entry


@router.post("/manual", response_model=JournalEntryDetail, status_code=status.HTTP_201_CREATED)
async def create_manual_journal(
    payload: JournalEntryManualCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    service = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    return await service.create_manual_entry(
        entry_date=payload.entry_date,
        base_currency=payload.base_currency,
        memo=payload.memo,
        source_type=payload.source_type,
        source_id=payload.source_id,
        lines=payload.lines,
    )


@router.post("/{entry_id}/post", response_model=JournalEntryDetail)
async def post_journal_entry(
    entry_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    service = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    return await service.post_entry(entry_id)


@router.post("/{entry_id}/reverse", response_model=JournalEntryDetail)
async def reverse_journal_entry(
    entry_id: UUID,
    payload: JournalEntryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    service = LedgerService(session=session, tenant_id=tenant_id, actor_id=actor_id)
    return await service.reverse_entry(entry_id, reason=payload.reason)


@router.post("/period-locks", response_model=AccountingPeriodLockPublic, status_code=status.HTTP_201_CREATED)
async def lock_accounting_period_endpoint(
    payload: AccountingPeriodLockCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await lock_accounting_period(
        session,
        tenant_id=tenant_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        actor_id=actor_id,
        commit=True,
    )


@router.delete("/period-locks/{lock_id}", response_model=AccountingPeriodLockPublic)
async def unlock_accounting_period_endpoint(
    lock_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await unlock_accounting_period(
        session,
        tenant_id=tenant_id,
        lock_id=lock_id,
        actor_id=actor_id,
        commit=True,
    )


__all__ = ["router"]
