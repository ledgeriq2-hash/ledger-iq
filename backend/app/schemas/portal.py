from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List
from uuid import UUID

from app.schemas.common import BaseSchema
from app.schemas.customer import CustomerPublic
from app.schemas.invoice import InvoicePublic
from app.schemas.payment import PaymentPublic
from app.schemas.supplier import SupplierPublic


class PortalSettings(BaseSchema):
    notifications: bool = True
    language: str = "en"


class PortalSettingsUpdate(BaseSchema):
    notifications: bool | None = None
    language: str | None = None


class PortalActivityItem(BaseSchema):
    id: UUID | None = None
    title: str
    description: str | None = None
    timestamp: str


class PortalOrder(BaseSchema):
    id: UUID
    reference: str | None = None
    status: str | None = None
    total_amount: Decimal
    currency: str
    order_date: date | None = None
    description: str | None = None


class PortalSupplierPayment(BaseSchema):
    id: UUID
    reference: str | None = None
    amount: Decimal
    currency: str
    paid_at: str | None = None
    status: str | None = None
    description: str | None = None


class CustomerInvoicesResponse(BaseSchema):
    invoices: List[InvoicePublic]


class CustomerPaymentsResponse(BaseSchema):
    payments: List[PaymentPublic]


class SupplierOrdersResponse(BaseSchema):
    orders: List[PortalOrder]


class SupplierPaymentsResponse(BaseSchema):
    payments: List[PortalSupplierPayment]


class CustomerPortalResponse(BaseSchema):
    customer: CustomerPublic
    invoices: List[InvoicePublic]
    payments: List[PaymentPublic]
    settings: PortalSettings
    recent_activity: List[PortalActivityItem]


class SupplierPortalResponse(BaseSchema):
    supplier: SupplierPublic
    orders: List[PortalOrder]
    payments: List[PortalSupplierPayment]
    settings: PortalSettings
    recent_activity: List[PortalActivityItem]


__all__ = [
    "PortalSettings",
    "PortalSettingsUpdate",
    "PortalActivityItem",
    "PortalOrder",
    "PortalSupplierPayment",
    "CustomerInvoicesResponse",
    "CustomerPaymentsResponse",
    "SupplierOrdersResponse",
    "SupplierPaymentsResponse",
    "CustomerPortalResponse",
    "SupplierPortalResponse",
]
