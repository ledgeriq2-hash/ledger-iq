from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, IDTimestampMixin


class JournalLineBase(BaseSchema):
    account_id: UUID
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    line_currency: str
    fx_rate: Decimal | None = None
    memo: str | None = None
    dimensions: dict | None = None
    tax_code: str | None = None


class JournalLineCreate(JournalLineBase):
    pass


class JournalLinePublic(IDTimestampMixin, JournalLineBase):
    id: UUID
    line_no: int
    debit_base: Decimal
    credit_base: Decimal


class JournalEntrySummary(IDTimestampMixin, BaseSchema):
    id: UUID
    entry_no: str
    entry_date: date
    period_year: int
    period_month: int
    status: str
    source_type: str
    source_id: UUID | None = None
    memo: str | None = None
    base_currency: str
    total_debit_base: Decimal
    total_credit_base: Decimal
    reversal_of_entry_id: UUID | None = None


class JournalEntryDetail(JournalEntrySummary):
    posting_date: datetime | None = None
    posted_at: datetime | None = None
    created_by: UUID | None = None
    approved_by: UUID | None = None
    lines: list[JournalLinePublic] = Field(validation_alias="ledger_lines")


class JournalEntryList(BaseSchema):
    items: list[JournalEntrySummary]


class JournalEntryManualCreate(BaseSchema):
    entry_date: date
    memo: str | None = None
    base_currency: str = "USD"
    source_type: str = "manual"
    source_id: UUID | None = None
    lines: list[JournalLineCreate]


class JournalEntryReverseRequest(BaseSchema):
    reason: str


__all__ = [
    "JournalLineBase",
    "JournalLineCreate",
    "JournalLinePublic",
    "JournalEntrySummary",
    "JournalEntryDetail",
    "JournalEntryList",
    "JournalEntryManualCreate",
    "JournalEntryReverseRequest",
]
