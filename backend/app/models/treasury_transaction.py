from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.supplier import Supplier
from app.models.treasury import Treasury
from app.models.user import User


class TreasuryTransaction(BaseModel):
    __tablename__ = "treasury_transactions"

    treasury_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasuries.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    movement_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))
    party_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversed_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasury_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_reversed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    is_voided: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    voided_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    treasury: Mapped[Treasury | None] = relationship("Treasury", lazy="joined")
    customer: Mapped[Customer | None] = relationship("Customer", lazy="joined")
    supplier: Mapped[Supplier | None] = relationship("Supplier", lazy="joined")
    employee: Mapped[Employee | None] = relationship("Employee", lazy="joined")
    voided_by_user: Mapped[User | None] = relationship("User", lazy="joined")

    __table_args__ = (
        Index("ix_treasury_transactions_tenant_id", "tenant_id"),
        Index("ix_treasury_transactions_created_at", "created_at"),
        Index("ix_treasury_transactions_event_date", "event_date"),
        Index("ix_treasury_transactions_treasury_id", "treasury_id"),
        Index("ix_treasury_transactions_direction", "direction"),
        Index("ix_treasury_transactions_customer_id", "customer_id"),
        Index("ix_treasury_transactions_supplier_id", "supplier_id"),
        Index("ix_treasury_transactions_employee_id", "employee_id"),
    )


__all__ = ["TreasuryTransaction"]
