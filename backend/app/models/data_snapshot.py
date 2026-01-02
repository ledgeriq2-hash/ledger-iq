from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    granularity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filters_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rows_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "filters_hash", name="uq_data_snapshots_tenant_source_filters_hash"),
        Index("ix_data_snapshots_tenant_source_created_at", "tenant_id", "source", "created_at"),
    )


__all__ = ["DataSnapshot"]

