from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class Customer(BaseModel):
    __tablename__ = "customers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CustomerStatus] = mapped_column(
        SqlEnum(CustomerStatus, name="customer_status"),
        nullable=False,
        server_default=CustomerStatus.ACTIVE.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_customers_tenant_code"),
        Index("ix_customers_tenant_id", "tenant_id"),
        Index("ix_customers_created_at", "created_at"),
    )


__all__ = ["Customer", "CustomerStatus"]
