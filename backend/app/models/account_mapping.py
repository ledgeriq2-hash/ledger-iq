from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AccountMapping(BaseModel):
    __tablename__ = "account_mappings"

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    account: Mapped["Account"] = relationship("Account", lazy="joined")

    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_account_mappings_tenant_key"),
        Index("ix_account_mappings_tenant_id", "tenant_id"),
        Index("ix_account_mappings_created_at", "created_at"),
    )


__all__ = ["AccountMapping"]
