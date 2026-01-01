from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin
from app.schemas.journal_entry import JournalEntryLineCreate

MovementType = Literal[
    "receipt",
    "disbursement",
    "expense",
    "payroll_payout",
    "supplier_payment",
    "employee_payment",
]


class TreasuryMovementBase(BaseSchema):
    amount: Decimal
    reference_type: str | None = None
    reference_id: UUID
    description: str | None = None
    entry_date: date | None = None


class TreasuryReceiptCreate(TreasuryMovementBase):
    customer_id: UUID


class TreasurySupplierPaymentCreate(TreasuryMovementBase):
    supplier_id: UUID


class TreasuryExpenseCreate(TreasuryMovementBase):
    supplier_id: UUID


class TreasuryPayrollPayoutCreate(TreasuryMovementBase):
    employee_id: UUID


class TreasuryEmployeePaymentCreate(TreasuryMovementBase):
    employee_id: UUID


class TreasuryDisbursementCreate(TreasuryMovementBase):
    counterparty_account_id: UUID
    counterparty_entity_type: str | None = None
    counterparty_entity_id: UUID | None = None


class TreasuryMovementResponse(IDTimestampMixin):
    id: UUID
    journal_entry_id: UUID | None
    treasury_id: UUID
    movement_type: MovementType
    direction: Literal["in", "out"]
    amount: Decimal
    reference_type: str | None
    reference_id: UUID | None
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    employee_id: UUID | None = None
    description: str | None = None


class TreasuryMovementListResponse(PaginatedResponse[TreasuryMovementResponse]):
    items: list[TreasuryMovementResponse] = Field(..., alias="movements")


class TreasuryReverseRequest(BaseSchema):
    reason: str | None = None


class TreasuryVoidRequest(BaseSchema):
    reason: str | None = None


class TreasuryAdjustmentRequest(BaseSchema):
    reason: str | None = None
    lines: list[JournalEntryLineCreate] = Field(..., min_length=1)
