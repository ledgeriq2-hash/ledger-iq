from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class InventoryUnit(BaseModel):
    __tablename__ = "inventory_units"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ratio_to_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        server_default=text("1"),
    )
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_units_tenant_code"),
        Index("ix_units_tenant_id", "tenant_id"),
        Index("ix_units_created_at", "created_at"),
    )


Unit = InventoryUnit

__all__ = ["InventoryUnit", "Unit"]
