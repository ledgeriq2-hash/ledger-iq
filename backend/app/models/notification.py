from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.user import User


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship("User", lazy="joined")

    __table_args__ = (
        Index("ix_notifications_tenant_id", "tenant_id"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_user_id", "user_id"),
    )


__all__ = ["Notification"]
