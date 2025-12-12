from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Product(BaseModel):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    is_service: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_products_tenant_id", "tenant_id"),
        Index("ix_products_created_at", "created_at"),
    )


__all__ = ["Product"]
