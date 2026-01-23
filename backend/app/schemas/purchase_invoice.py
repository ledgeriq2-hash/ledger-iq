from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.models.purchase_invoice import PurchaseInvoiceStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class PurchaseInvoiceLineBase(BaseSchema):
    line_no: int
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    expense_account_id: UUID

    @field_validator("quantity", "unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceLineCreate(PurchaseInvoiceLineBase):
    pass


class PurchaseInvoiceLineUpdate(BaseSchema):
    line_no: int | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    expense_account_id: UUID | None = None

    @field_validator("quantity", "unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceLineOut(IDTimestampMixin, PurchaseInvoiceLineBase):
    id: UUID


class PurchaseInvoiceBase(BaseSchema):
    vendor_id: UUID
    invoice_no: str
    invoice_date: date
    currency_code: str | None = None

    @field_validator("invoice_no")
    @classmethod
    def invoice_no_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    lines: list[PurchaseInvoiceLineCreate] = Field(..., min_length=1)


class PurchaseInvoiceUpdate(BaseSchema):
    vendor_id: UUID | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    currency_code: str | None = None
    lines: list[PurchaseInvoiceLineUpdate] | None = Field(default=None, min_length=1)

    @field_validator("invoice_no")
    @classmethod
    def update_invoice_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class PurchaseInvoiceOut(IDTimestampMixin, PurchaseInvoiceBase):
    id: UUID
    status: PurchaseInvoiceStatus = PurchaseInvoiceStatus.DRAFT
    total_amount: Decimal = Decimal("0")
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    lines: list[PurchaseInvoiceLineOut] | None = None

    @field_validator("total_amount")
    @classmethod
    def total_amount_non_negative(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceListOut(PaginatedResponse[PurchaseInvoiceOut]):
    pass


__all__ = [
    "PurchaseInvoiceLineBase",
    "PurchaseInvoiceLineCreate",
    "PurchaseInvoiceLineUpdate",
    "PurchaseInvoiceLineOut",
    "PurchaseInvoiceBase",
    "PurchaseInvoiceCreate",
    "PurchaseInvoiceUpdate",
    "PurchaseInvoiceOut",
    "PurchaseInvoiceListOut",
    "PurchaseInvoiceStatus",
]
