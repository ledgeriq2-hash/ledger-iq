from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class GdprRequest(BaseModel):
    __tablename__ = "gdpr_requests"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # export | delete
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    initiated_by: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "action", "created_at", name="uq_gdpr_request_unique_run"),
        Index("ix_gdpr_requests_tenant_created", "tenant_id", "created_at"),
    )


__all__ = ["GdprRequest"]
