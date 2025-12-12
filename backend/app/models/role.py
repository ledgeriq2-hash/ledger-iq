from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_roles_tenant_id", "tenant_id"),
        Index("ix_roles_created_at", "created_at"),
    )


__all__ = ["Role"]
