from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class VendorStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Vendor(BaseModel):
    __tablename__ = "vendors"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[VendorStatus] = mapped_column(
        SqlEnum(VendorStatus, name="vendor_status"),
        nullable=False,
        server_default=VendorStatus.ACTIVE.value,
    )
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_vendors_tenant_code"),
        Index("ix_vendors_tenant_id", "tenant_id"),
        Index("ix_vendors_created_at", "created_at"),
        Index("ix_vendors_tenant_status", "tenant_id", "status"),
        Index("ix_vendors_tenant_name", "tenant_id", "name"),
    )


__all__ = ["Vendor", "VendorStatus"]
