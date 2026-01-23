from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.models.treasury_cash_transaction import CashTransactionStatus, CashTransactionType
from app.schemas.common import BaseSchema, IDTimestampMixin


class CashAccountBase(BaseSchema):
    name: str
    account_id: UUID
    description: str | None = None


class CashAccountCreate(CashAccountBase):
    pass


class CashAccountPublic(IDTimestampMixin, CashAccountBase):
    id: UUID


class CashAccountList(BaseSchema):
    items: list[CashAccountPublic]


class CashTransactionBase(BaseSchema):
    transaction_type: CashTransactionType
    amount: Decimal
    posting_date: date | None = None
    description: str | None = None
    cash_account_id: UUID | None = None
    counterparty_account_id: UUID | None = None
    from_cash_account_id: UUID | None = None
    to_cash_account_id: UUID | None = None


class CashTransactionCreate(CashTransactionBase):
    pass


class CashTransactionPublic(IDTimestampMixin, BaseSchema):
    id: UUID
    transaction_type: CashTransactionType
    status: CashTransactionStatus
    amount: Decimal
    posting_date: date
    description: str | None = None
    cash_account_id: UUID | None = None
    counterparty_account_id: UUID | None = None
    from_cash_account_id: UUID | None = None
    to_cash_account_id: UUID | None = None
    journal_entry_id: UUID | None = None
    reversal_journal_entry_id: UUID | None = None
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    reversal_reason: str | None = None


class CashTransactionList(BaseSchema):
    items: list[CashTransactionPublic]


class CashTransactionReverseRequest(BaseSchema):
    reason: str


__all__ = [
    "CashAccountBase",
    "CashAccountCreate",
    "CashAccountPublic",
    "CashAccountList",
    "CashTransactionBase",
    "CashTransactionCreate",
    "CashTransactionPublic",
    "CashTransactionList",
    "CashTransactionReverseRequest",
]
