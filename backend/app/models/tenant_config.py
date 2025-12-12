from __future__ import annotations

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenantConfig(BaseModel):
    __tablename__ = "tenant_configs"

    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_soft_launch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_configs_tenant_id"),)


__all__ = ["TenantConfig"]
