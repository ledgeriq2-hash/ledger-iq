from __future__ import annotations

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BillingPlan(BaseModel):
    __tablename__ = "billing_plans"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="usd")
    interval: Mapped[str] = mapped_column(String(20), nullable=False, default="month")
    limits_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("code", name="uq_billing_plans_code"),
        Index("ix_billing_plans_code", "code"),
    )


__all__ = ["BillingPlan"]
