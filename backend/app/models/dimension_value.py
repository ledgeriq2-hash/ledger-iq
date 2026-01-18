from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.dimension import Dimension


class DimensionValue(BaseModel):
    __tablename__ = "dimension_values"

    dimension_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dimensions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    dimension: Mapped["Dimension"] = relationship("Dimension", back_populates="values", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "dimension_id",
            "code",
            name="uq_dimension_values_tenant_dimension_code",
        ),
        Index("ix_dimension_values_tenant_id", "tenant_id"),
        Index("ix_dimension_values_dimension_id", "dimension_id"),
        Index("ix_dimension_values_created_at", "created_at"),
    )


__all__ = ["DimensionValue"]
