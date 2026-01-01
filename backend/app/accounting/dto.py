from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from app.schemas.common import BaseSchema

EntityType = Literal["client", "supplier", "worker", "expense"]
Direction = Literal["in", "out"]


class LedgerLineInput(BaseSchema):
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    currency_amount: Decimal | None = None
    entity_type: EntityType | None = None
    entity_id: UUID | None = None
    reference_type: str
    reference_id: UUID
    description: str | None = None


class TreasuryMovementInput(BaseSchema):
    treasury_id: UUID | None = None
    amount: Decimal
    direction: Direction
    reference_type: str
    reference_id: UUID
    movement_type: str | None = None
    party_type: str | None = None
    party_id: UUID | None = None
    reversed_of_id: UUID | None = None


class RecordFinancialTransactionInput(BaseSchema):
    tenant_id: UUID
    actor_id: UUID | None = None
    date: date
    description: str | None = None
    reference_type: str
    reference_id: UUID
    lines: list[LedgerLineInput]
    treasury_movement: TreasuryMovementInput | None = None
    entry_metadata: dict[str, Any] | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None


class RecordFinancialTransactionOutput(BaseSchema):
    journal_entry_id: UUID
    treasury_transaction_id: UUID | None = None
    audit_log_id: UUID


__all__ = [
    "EntityType",
    "Direction",
    "LedgerLineInput",
    "TreasuryMovementInput",
    "RecordFinancialTransactionInput",
    "RecordFinancialTransactionOutput",
]
