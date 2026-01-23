from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.unit import Unit


class UnitConversion(BaseModel):
    __tablename__ = "unit_conversions"

    from_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    multiplier: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    from_unit: Mapped[Unit] = relationship("Unit", foreign_keys=[from_unit_id], lazy="joined")
    to_unit: Mapped[Unit] = relationship("Unit", foreign_keys=[to_unit_id], lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "from_unit_id",
            "to_unit_id",
            name="uq_unit_conversions_tenant_from_to",
        ),
        CheckConstraint("multiplier > 0", name="ck_unit_conversions_multiplier_positive"),
        Index("ix_unit_conversions_tenant_id", "tenant_id"),
        Index("ix_unit_conversions_created_at", "created_at"),
        Index("ix_unit_conversions_from_unit_id", "from_unit_id"),
        Index("ix_unit_conversions_to_unit_id", "to_unit_id"),
    )


__all__ = ["UnitConversion"]
