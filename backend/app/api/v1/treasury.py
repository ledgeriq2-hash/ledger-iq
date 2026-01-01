from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, require_roles
from app.core.pagination import PaginationParams, paginate_query
from app.models.journal_entry import JournalEntry
from app.models.treasury_transaction import TreasuryTransaction
from app.schemas.journal_entry import JournalEntryLineCreate, JournalEntryPublic
from app.schemas.treasury import (
    MovementType,
    TreasuryAdjustmentRequest,
    TreasuryDisbursementCreate,
    TreasuryEmployeePaymentCreate,
    TreasuryExpenseCreate,
    TreasuryMovementListResponse,
    TreasuryMovementResponse,
    TreasuryPayrollPayoutCreate,
    TreasuryReceiptCreate,
    TreasurySupplierPaymentCreate,
    TreasuryVoidRequest,
    TreasuryReverseRequest,
)
from app.services import journal_service, treasury_service

router = APIRouter(prefix="/treasury", dependencies=[Depends(require_roles([OWNER, ADMIN, ACCOUNTANT]))])


async def _to_response(session: AsyncSession, tx: TreasuryTransaction) -> TreasuryMovementResponse:
    description = None
    if tx.journal_entry_id:
        entry = await session.get(JournalEntry, tx.journal_entry_id)
        description = entry.description if entry else None
    return TreasuryMovementResponse(
        id=tx.id,
        treasury_id=tx.treasury_id,
        journal_entry_id=tx.journal_entry_id,
        movement_type=tx.movement_type,  # type: ignore[arg-type]
        direction=tx.direction,  # type: ignore[arg-type]
        amount=Decimal(str(tx.amount or 0)).quantize(Decimal("0.01")),
        reference_type=tx.reference_type,
        reference_id=tx.reference_id,
        customer_id=tx.customer_id,
        supplier_id=tx.supplier_id,
        employee_id=tx.employee_id,
        description=description,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


async def _get_movement(session: AsyncSession, tenant_id: UUID, movement_id: UUID) -> TreasuryTransaction:
    movement = await session.get(TreasuryTransaction, movement_id)
    if not movement or movement.tenant_id != tenant_id:
        raise AppException(
            code="treasury_movement_not_found",
            message="Treasury movement not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    return movement


@router.get("/{treasury_id}/movements", response_model=TreasuryMovementListResponse)
async def list_movements(
    treasury_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
    pagination: PaginationParams = Depends(),
):
    stmt = (
        select(TreasuryTransaction)
        .where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.treasury_id == treasury_id,
        )
        .order_by(TreasuryTransaction.created_at.desc())
    )
    movements, total = await paginate_query(session, stmt, pagination)
    items: list[TreasuryMovementResponse] = []
    for tx in movements:
        items.append(await _to_response(session, tx))
    return TreasuryMovementListResponse.from_results(
        items=items,
        total=total,
        params=pagination,
    )


@router.post("/{treasury_id}/movements/receipt", response_model=TreasuryMovementResponse)
async def create_receipt(
    treasury_id: UUID,
    payload: TreasuryReceiptCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_receipt(
        session,
        tenant_id,
        amount=payload.amount,
        customer_id=payload.customer_id,
        reference_type=payload.reference_type or "treasury_receipt",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/{treasury_id}/movements/supplier-payment", response_model=TreasuryMovementResponse)
async def create_supplier_payment(
    treasury_id: UUID,
    payload: TreasurySupplierPaymentCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_supplier_payment(
        session,
        tenant_id,
        amount=payload.amount,
        supplier_id=payload.supplier_id,
        reference_type=payload.reference_type or "supplier_payment",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/{treasury_id}/movements/expense", response_model=TreasuryMovementResponse)
async def create_expense(
    treasury_id: UUID,
    payload: TreasuryExpenseCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_expense(
        session,
        tenant_id,
        amount=payload.amount,
        supplier_id=payload.supplier_id,
        reference_type=payload.reference_type or "expense",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/{treasury_id}/movements/employee-payment", response_model=TreasuryMovementResponse)
async def create_employee_payment(
    treasury_id: UUID,
    payload: TreasuryEmployeePaymentCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_employee_payment(
        session,
        tenant_id,
        amount=payload.amount,
        employee_id=payload.employee_id,
        reference_type=payload.reference_type or "employee_payment",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/{treasury_id}/movements/payroll-payout", response_model=TreasuryMovementResponse)
async def create_payroll_payout(
    treasury_id: UUID,
    payload: TreasuryPayrollPayoutCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_payroll_payout(
        session,
        tenant_id,
        amount=payload.amount,
        employee_id=payload.employee_id,
        reference_type=payload.reference_type or "payroll_payout",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/{treasury_id}/movements/disbursement", response_model=TreasuryMovementResponse)
async def create_disbursement(
    treasury_id: UUID,
    payload: TreasuryDisbursementCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await treasury_service.create_disbursement(
        session,
        tenant_id,
        amount=payload.amount,
        counterparty_account_id=payload.counterparty_account_id,
        counterparty_entity_type=payload.counterparty_entity_type,
        counterparty_entity_id=payload.counterparty_entity_id,
        reference_type=payload.reference_type or "treasury_disbursement",
        reference_id=payload.reference_id,
        description=payload.description,
        entry_date=payload.entry_date,
        treasury_id=treasury_id,
        actor_id=actor_id,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/movements/{movement_id}/reverse", response_model=TreasuryMovementResponse)
async def reverse_movement(
    movement_id: UUID,
    payload: TreasuryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await _get_movement(session, tenant_id, movement_id)
    if movement.is_voided:
        raise AppException(
            code="treasury_movement_voided",
            message="Cannot reverse a voided movement",
            http_status=status.HTTP_409_CONFLICT,
        )
    reversed_entry = await journal_service.reverse_journal_entry(
        session,
        tenant_id,
        movement.journal_entry_id,
        actor_id=actor_id,
        reason=payload.reason,
    )
    if not reversed_entry.treasury_transaction_id:
        raise AppException(
            code="treasury_reversal_missing",
            message="Reversal created without treasury movement",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    reversed_tx = await session.get(TreasuryTransaction, reversed_entry.treasury_transaction_id)
    if not reversed_tx:
        raise AppException(
            code="treasury_reversal_missing",
            message="Reversal treasury movement missing",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    await session.refresh(reversed_tx)
    if movement.id != reversed_tx.reversed_of_id:
        reversed_tx.reversed_of_id = movement.id
    return await _to_response(session, reversed_tx)


@router.post("/movements/{movement_id}/void", response_model=TreasuryMovementResponse)
async def void_movement(
    movement_id: UUID,
    payload: TreasuryVoidRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    movement = await _get_movement(session, tenant_id, movement_id)
    voided_entry = await journal_service.void_journal_entry(
        session,
        tenant_id,
        movement.journal_entry_id,
        actor_id=actor_id,
        reason=payload.reason,
    )
    await session.refresh(movement)
    return await _to_response(session, movement)


@router.post("/movements/{movement_id}/adjust", response_model=JournalEntryPublic)
async def adjust_movement(
    movement_id: UUID,
    payload: TreasuryAdjustmentRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    movement = await _get_movement(session, tenant_id, movement_id)
    actor_id = getattr(request.state, "user_id", None)
    lines = [line.model_dump() for line in payload.lines]
    return await journal_service.adjust_journal_entry(
        session,
        tenant_id,
        movement.journal_entry_id,
        actor_id=actor_id,
        reason=payload.reason,
        lines=lines,
        idempotency_key=idempotency_key or "",
    )
