from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AiRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    scenario: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'baseline'"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'approved'"))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("status IN ('approved', 'revoked')", name="ck_ai_runs_status"),
        CheckConstraint("char_length(payload_hash) = 64", name="ck_ai_runs_payload_hash_len"),
        CheckConstraint(
            "status <> 'revoked' OR revoked_at IS NOT NULL",
            name="ck_ai_runs_revoked_requires_timestamp",
        ),
        Index("ix_ai_runs_client_created_at", "client_id", text("created_at DESC")),
        Index("ix_ai_runs_client_status", "client_id", "status"),
        Index("ix_ai_runs_client_scenario", "client_id", "scenario"),
    )


__all__ = ["AiRun"]
