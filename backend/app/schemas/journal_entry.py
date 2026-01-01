from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class JournalEntryLineBase(BaseSchema):
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    line_description: str | None = None
    currency_amount: Decimal | None = None
    entity_type: str | None = None  # client|supplier|worker|expense
    entity_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None


class JournalEntryLineCreate(JournalEntryLineBase):
    pass


class JournalEntryLineUpdate(BaseSchema):
    account_id: Optional[UUID] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    line_description: Optional[str] = None
    currency_amount: Optional[Decimal] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None


class JournalEntryLinePublic(IDTimestampMixin, JournalEntryLineBase):
    id: UUID


class JournalEntryBase(BaseSchema):
    date: date
    description: Optional[str] = None
    reference: Optional[str] = None
    is_posted: bool = False
    currency_code: Optional[str] = None
    fx_rate: Optional[Decimal] = None
    source_module: Optional[str] = None
    source_id: Optional[UUID] = None
    reversed_of_id: Optional[UUID] = None
    adjusted_of_id: Optional[UUID] = None
    treasury_transaction_id: Optional[UUID] = None
    is_reversed: Optional[bool] = None
    is_voided: Optional[bool] = None


class JournalEntryCreate(JournalEntryBase):
    lines: List[JournalEntryLineCreate]


class JournalEntryUpdate(BaseSchema):
    date: Optional[date] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    is_posted: Optional[bool] = None
    currency_code: Optional[str] = None
    fx_rate: Optional[Decimal] = None
    source_module: Optional[str] = None
    source_id: Optional[UUID] = None
    reversed_of_id: Optional[UUID] = None
    lines: Optional[List[JournalEntryLineUpdate]] = None


class JournalEntryPublic(IDTimestampMixin, JournalEntryBase):
    id: UUID
    lines: List[JournalEntryLinePublic]


class JournalEntryList(BaseSchema):
    items: List[JournalEntryPublic]


class JournalEntryReverseRequest(BaseSchema):
    reason: Optional[str] = None


class JournalEntryVoidRequest(BaseSchema):
    reason: Optional[str] = None


class JournalEntryAdjustmentRequest(BaseSchema):
    reason: Optional[str] = None
    lines: List[JournalEntryLineCreate]


__all__ = [
    "JournalEntryBase",
    "JournalEntryCreate",
    "JournalEntryUpdate",
    "JournalEntryPublic",
    "JournalEntryList",
    "JournalEntryLineBase",
    "JournalEntryLineCreate",
    "JournalEntryLineUpdate",
    "JournalEntryLinePublic",
    "JournalEntryReverseRequest",
    "JournalEntryVoidRequest",
    "JournalEntryAdjustmentRequest",
]
