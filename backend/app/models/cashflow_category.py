from __future__ import annotations

from enum import Enum

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class CashflowType(str, Enum):
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"


class CashflowCategory(BaseModel):
    __tablename__ = "cashflow_categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CashflowType] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_cashflow_categories_tenant_id", "tenant_id"),
        Index("ix_cashflow_categories_created_at", "created_at"),
    )


__all__ = ["CashflowCategory", "CashflowType"]
