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
    product_id: UUID | None = None
    unit_id: UUID | None = None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    vat_rate: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    expense_account_id: UUID

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value

    @field_validator("vat_rate", "vat_amount")
    @classmethod
    def vat_non_negative(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceLineCreate(PurchaseInvoiceLineBase):
    pass


class PurchaseInvoiceLineUpdate(BaseSchema):
    line_no: int | None = None
    description: str | None = None
    product_id: UUID | None = None
    unit_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    vat_rate: Decimal | None = None
    vat_amount: Decimal | None = None
    expense_account_id: UUID | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value

    @field_validator("vat_rate", "vat_amount")
    @classmethod
    def vat_non_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceLineOut(IDTimestampMixin, PurchaseInvoiceLineBase):
    id: UUID
    base_amount: Decimal | None = None


class PurchaseInvoiceBase(BaseSchema):
    vendor_id: UUID
    invoice_no: str | None = None
    invoice_date: date
    due_date: date | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None

    @field_validator("invoice_no")
    @classmethod
    def invoice_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    lines: list[PurchaseInvoiceLineCreate] = Field(..., min_length=1)


class PurchaseInvoiceUpdate(BaseSchema):
    vendor_id: UUID | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None
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
    subtotal: Decimal = Decimal("0")
    vat_total: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    base_subtotal: Decimal = Decimal("0")
    base_vat_total: Decimal = Decimal("0")
    base_total: Decimal = Decimal("0")
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    posting_journal_entry_id: UUID | None = None
    reversal_journal_entry_id: UUID | None = None
    lines: list[PurchaseInvoiceLineOut] | None = None

    @field_validator("total_amount")
    @classmethod
    def total_amount_non_negative(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class PurchaseInvoiceListOut(PaginatedResponse[PurchaseInvoiceOut]):
    pass


class PurchaseBillDraftBase(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    vendor_id: UUID | None = None
    invoice_no: str | None = Field(default=None, alias="bill_no")
    invoice_date: date
    due_date: date | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None

    @field_validator("invoice_no")
    @classmethod
    def bill_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class PurchaseBillCreateDraft(PurchaseBillDraftBase):
    lines: list[PurchaseInvoiceLineCreate] = Field(..., min_length=1)


class PurchaseBillUpdateDraft(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    vendor_id: UUID | None = None
    invoice_no: str | None = Field(default=None, alias="bill_no")
    invoice_date: date | None = None
    due_date: date | None = None
    currency_code: str | None = None
    fx_rate: Decimal | None = None
    memo: str | None = None
    lines: list[PurchaseInvoiceLineUpdate] | None = Field(default=None, min_length=1)

    @field_validator("invoice_no")
    @classmethod
    def update_bill_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class PurchaseBillLineRead(IDTimestampMixin, PurchaseInvoiceLineBase):
    id: UUID
    line_total: Decimal | None = None
    base_amount: Decimal | None = None


class PurchaseBillLineCreate(PurchaseInvoiceLineCreate):
    pass


class PurchaseBillLineUpdate(PurchaseInvoiceLineUpdate):
    pass


class PurchaseBillRead(IDTimestampMixin, PurchaseBillDraftBase):
    id: UUID
    status: PurchaseInvoiceStatus = PurchaseInvoiceStatus.DRAFT
    subtotal: Decimal = Decimal("0")
    vat_total: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    base_subtotal: Decimal = Decimal("0")
    base_vat_total: Decimal = Decimal("0")
    base_total: Decimal = Decimal("0")
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    posting_journal_entry_id: UUID | None = None
    reversal_journal_entry_id: UUID | None = None
    lines: list[PurchaseBillLineRead] | None = None


class PurchaseBillListOut(PaginatedResponse[PurchaseBillRead]):
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
    "PurchaseBillDraftBase",
    "PurchaseBillLineCreate",
    "PurchaseBillLineUpdate",
    "PurchaseBillCreateDraft",
    "PurchaseBillUpdateDraft",
    "PurchaseBillRead",
    "PurchaseBillLineRead",
    "PurchaseBillListOut",
]
