from __future__ import annotations

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Unit(BaseModel):
    __tablename__ = "units"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_units_tenant_code"),
        Index("ix_units_tenant_id", "tenant_id"),
        Index("ix_units_created_at", "created_at"),
    )


__all__ = ["Unit"]
