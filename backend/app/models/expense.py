from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.supplier import Supplier


class Expense(BaseModel):
    __tablename__ = "expenses"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped[Supplier] = relationship("Supplier", lazy="joined")

    __table_args__ = (
        Index("ix_expenses_tenant_id", "tenant_id"),
        Index("ix_expenses_created_at", "created_at"),
        Index("ix_expenses_supplier_id", "supplier_id"),
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_event_date", "event_date"),
    )


__all__ = ["Expense"]
