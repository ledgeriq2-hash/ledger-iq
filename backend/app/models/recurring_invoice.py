from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.customer import Customer


class RecurringInvoice(BaseModel):
    __tablename__ = "recurring_invoices"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[int] = mapped_column(nullable=False, default=1)
    day_of_month: Mapped[int | None] = mapped_column(nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    template_json: Mapped[str] = mapped_column(Text, nullable=False)

    customer: Mapped[Customer] = relationship("Customer", lazy="joined")

    __table_args__ = (
        Index("ix_recurring_invoices_tenant_id", "tenant_id"),
        Index("ix_recurring_invoices_created_at", "created_at"),
        Index("ix_recurring_invoices_customer_id", "customer_id"),
    )


__all__ = ["RecurringInvoice"]
