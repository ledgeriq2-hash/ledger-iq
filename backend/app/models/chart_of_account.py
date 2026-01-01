from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class ChartOfAccount(BaseModel):
    __tablename__ = "chart_of_accounts"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        "type",
        SqlEnum(AccountType, name="chart_of_account_type"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    __table_args__ = (
        Index("ix_chart_of_accounts_tenant_id", "tenant_id"),
        Index("ix_chart_of_accounts_created_at", "created_at"),
    )


__all__ = ["ChartOfAccount", "AccountType"]
