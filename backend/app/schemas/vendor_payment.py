from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_validator

from app.core.pagination import PaginatedResponse
from app.models.vendor_payment import VendorPaymentStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class VendorPaymentAllocationBase(BaseSchema):
    purchase_bill_id: UUID
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("amount must be greater than zero")
        return value


class VendorPaymentAllocationCreate(VendorPaymentAllocationBase):
    pass


class VendorPaymentAllocationUpdate(BaseSchema):
    purchase_bill_id: UUID | None = None
    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("amount must be greater than zero")
        return value


class VendorPaymentAllocationRead(IDTimestampMixin, VendorPaymentAllocationBase):
    id: UUID


class VendorPaymentDraftBase(BaseSchema):
    vendor_id: UUID | None = None
    payment_no: str | None = None
    payment_date: date
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

    @field_validator("payment_no")
    @classmethod
    def payment_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("payment_no must not be blank")
        return cleaned


class VendorPaymentCreateDraft(VendorPaymentDraftBase):
    pass


class VendorPaymentUpdateDraft(BaseSchema):
    vendor_id: UUID | None = None
    payment_no: str | None = None
    payment_date: date | None = None
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

    @field_validator("payment_no")
    @classmethod
    def update_payment_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("payment_no must not be blank")
        return cleaned


class VendorPaymentRead(IDTimestampMixin, VendorPaymentDraftBase):
    id: UUID
    status: VendorPaymentStatus = VendorPaymentStatus.DRAFT
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    posting_journal_entry_id: UUID | None = None
    reversal_journal_entry_id: UUID | None = None
    base_amount_total: Decimal | None = None
    allocations: list[VendorPaymentAllocationRead] | None = None


class VendorPaymentListOut(PaginatedResponse[VendorPaymentRead]):
    pass


__all__ = [
    "VendorPaymentAllocationBase",
    "VendorPaymentAllocationCreate",
    "VendorPaymentAllocationUpdate",
    "VendorPaymentAllocationRead",
    "VendorPaymentDraftBase",
    "VendorPaymentCreateDraft",
    "VendorPaymentUpdateDraft",
    "VendorPaymentRead",
    "VendorPaymentListOut",
    "VendorPaymentStatus",
]
