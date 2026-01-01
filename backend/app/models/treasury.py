from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Treasury(BaseModel):
    __tablename__ = "treasuries"

    type: Mapped[str] = mapped_column(String(20), nullable=False)  # cash|bank|wallet
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    transactions = relationship(
        "TreasuryTransaction",
        back_populates="treasury",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_treasuries_tenant_id", "tenant_id"),
        Index("ix_treasuries_created_at", "created_at"),
    )


__all__ = ["Treasury"]

