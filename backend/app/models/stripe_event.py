from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StripeEvent(BaseModel):
    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __table_args__ = (UniqueConstraint("event_id", name="uq_stripe_events_event_id"),)


__all__ = ["StripeEvent"]
