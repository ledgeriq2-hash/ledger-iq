from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    __tablename__ = "accounts"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(16), nullable=False)

    parent_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )

    # ✅ الصحيح: اتحاد Optional جوه سترينج واحد
    parent: Mapped["Account | None"] = relationship(
        "Account",
        remote_side="Account.id",
        back_populates="children",
    )
    children: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="parent",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_accounts_tenant_code"),
        Index("ix_accounts_tenant_id", "tenant_id"),
        Index("ix_accounts_created_at", "created_at"),
    )


__all__ = ["Account"]
