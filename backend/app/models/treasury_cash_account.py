from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.account import Account


class TreasuryCashAccount(BaseModel):
    __tablename__ = "treasury_cash_accounts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    account: Mapped[Account] = relationship("Account", lazy="joined")

    __table_args__ = (
        Index("ix_treasury_cash_accounts_tenant_id", "tenant_id"),
        Index("ix_treasury_cash_accounts_created_at", "created_at"),
        Index("ix_treasury_cash_accounts_account_id", "account_id"),
        Index("ix_treasury_cash_accounts_name", "name"),
    )


__all__ = ["TreasuryCashAccount"]
