from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema
from app.schemas.customer import CustomerPublic
from app.schemas.invoice import InvoicePublic
from app.schemas.payment import PaymentPublic


class PortalLinkRequest(BaseSchema):
    client_id: UUID
    expires_in: int | None = None  # seconds


class PortalLinkResponse(BaseSchema):
    success: bool = True
    url: str
    expires_at: datetime | None = None
    token_id: UUID | None = None


class PortalActivityItem(BaseSchema):
    id: UUID | None = None
    title: str
    description: str | None = None
    timestamp: str


class PortalSummaryStats(BaseSchema):
    open_invoices: int = 0
    total_open_amount: Decimal = Decimal("0.00")


class PortalSummaryResponse(BaseSchema):
    client: CustomerPublic
    recent_activity: list[PortalActivityItem] = Field(default_factory=list)
    stats: PortalSummaryStats = Field(default_factory=PortalSummaryStats)


class PortalBalanceResponse(BaseSchema):
    client_id: UUID
    as_of_date: date
    balance: Decimal


class PortalInvoicesResponse(PaginatedResponse[InvoicePublic]):
    items: list[InvoicePublic] = Field(..., alias="invoices")
    model_config = {"from_attributes": True, "populate_by_name": True}


class PortalPaymentsResponse(PaginatedResponse[PaymentPublic]):
    items: list[PaymentPublic] = Field(..., alias="payments")
    model_config = {"from_attributes": True, "populate_by_name": True}


class PortalStatementResponse(BaseSchema):
    statement: dict[str, Any]


__all__ = [
    "PortalLinkRequest",
    "PortalLinkResponse",
    "PortalActivityItem",
    "PortalSummaryStats",
    "PortalSummaryResponse",
    "PortalBalanceResponse",
    "PortalInvoicesResponse",
    "PortalPaymentsResponse",
    "PortalStatementResponse",
]

