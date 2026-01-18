from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.dimension_value import DimensionValue


class Dimension(BaseModel):
    __tablename__ = "dimensions"

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    values: Mapped[list["DimensionValue"]] = relationship(
        "DimensionValue",
        back_populates="dimension",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_dimensions_tenant_key"),
        Index("ix_dimensions_tenant_id", "tenant_id"),
        Index("ix_dimensions_created_at", "created_at"),
        Index("ix_dimensions_key", "key"),
    )


__all__ = ["Dimension"]
