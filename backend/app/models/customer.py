from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Customer(BaseModel):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    __table_args__ = (
        Index("ix_customers_tenant_id", "tenant_id"),
        Index("ix_customers_created_at", "created_at"),
    )


__all__ = ["Customer"]
