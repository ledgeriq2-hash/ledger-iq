from __future__ import annotations

import uuid
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.unit import InventoryUnit


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Product(BaseModel):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        SqlEnum(ProductStatus, name="product_status"),
        nullable=False,
        server_default=ProductStatus.ACTIVE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    base_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    is_service: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    base_unit: Mapped["InventoryUnit | None"] = relationship("InventoryUnit", lazy="joined")

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
        UniqueConstraint("tenant_id", "code", name="uq_products_tenant_code"),
        Index("ix_products_tenant_id", "tenant_id"),
        Index("ix_products_created_at", "created_at"),
        Index("ix_products_tenant_status", "tenant_id", "status"),
        Index("ix_products_tenant_code", "tenant_id", "code"),
    )


__all__ = ["Product", "ProductStatus"]
