from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_validator

from app.core.pagination import PaginatedResponse
from app.models.customer_receipt import CustomerReceiptStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class CustomerReceiptAllocationBase(BaseSchema):
    sales_invoice_id: UUID
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("amount must be greater than zero")
        return value


class CustomerReceiptAllocationCreate(CustomerReceiptAllocationBase):
    pass


class CustomerReceiptAllocationUpdate(BaseSchema):
    sales_invoice_id: UUID | None = None
    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("amount must be greater than zero")
        return value


class CustomerReceiptAllocationRead(IDTimestampMixin, CustomerReceiptAllocationBase):
    id: UUID


class CustomerReceiptDraftBase(BaseSchema):
    customer_id: UUID | None = None
    receipt_no: str | None = None
    receipt_date: date
    amount_total: Decimal
    cash_account_id: UUID
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None

    @field_validator("amount_total")
    @classmethod
    def amount_total_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("amount_total must be greater than zero")
        return value

    @field_validator("receipt_no")
    @classmethod
    def receipt_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("receipt_no must not be blank")
        return cleaned


class CustomerReceiptCreateDraft(CustomerReceiptDraftBase):
    pass


class CustomerReceiptUpdateDraft(BaseSchema):
    customer_id: UUID | None = None
    receipt_no: str | None = None
    receipt_date: date | None = None
    amount_total: Decimal | None = None
    cash_account_id: UUID | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None

    @field_validator("amount_total")
    @classmethod
    def update_amount_total_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("amount_total must be greater than zero")
        return value

    @field_validator("receipt_no")
    @classmethod
    def update_receipt_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("receipt_no must not be blank")
        return cleaned


class CustomerReceiptRead(IDTimestampMixin, CustomerReceiptDraftBase):
    id: UUID
    status: CustomerReceiptStatus = CustomerReceiptStatus.DRAFT
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    posting_journal_entry_id: UUID | None = None
    reversal_journal_entry_id: UUID | None = None
    base_amount_total: Decimal | None = None
    allocations: list[CustomerReceiptAllocationRead] | None = None


class CustomerReceiptListOut(PaginatedResponse[CustomerReceiptRead]):
    pass


__all__ = [
    "CustomerReceiptAllocationBase",
    "CustomerReceiptAllocationCreate",
    "CustomerReceiptAllocationUpdate",
    "CustomerReceiptAllocationRead",
    "CustomerReceiptDraftBase",
    "CustomerReceiptCreateDraft",
    "CustomerReceiptUpdateDraft",
    "CustomerReceiptRead",
    "CustomerReceiptListOut",
    "CustomerReceiptStatus",
]
