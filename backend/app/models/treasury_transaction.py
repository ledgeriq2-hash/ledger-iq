from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.treasury import Treasury
from app.models.user import User

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.employee import Employee
    from app.models.supplier import Supplier


TREASURY_MOVEMENT_TYPES = (
    "receipt",
    "disbursement",
    "expense",
    "payroll_payout",
    "supplier_payment",
    "employee_payment",
)


class TreasuryTransaction(BaseModel):
    __tablename__ = "treasury_transactions"

    treasury_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasuries.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # in|out
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    reference_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))

    treasury: Mapped[Treasury] = relationship("Treasury", back_populates="transactions", lazy="joined")
    customer: Mapped["Customer"] = relationship("Customer", lazy="joined")
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="joined")
    employee: Mapped["Employee"] = relationship("Employee", lazy="joined")
    voided_by_user: Mapped["User"] = relationship("User", lazy="joined")

    __table_args__ = (
        Index("ix_treasury_transactions_tenant_id", "tenant_id"),
        Index("ix_treasury_transactions_created_at", "created_at"),
        Index("ix_treasury_transactions_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_treasury_transactions_event_date", "event_date"),
        Index("ix_treasury_transactions_reference", "reference_type", "reference_id"),
        Index("ix_treasury_transactions_treasury_id", "treasury_id"),
        Index("ix_treasury_transactions_journal_entry_id", "journal_entry_id"),
        Index("ix_treasury_transactions_movement_type", "movement_type"),
        Index("ix_treasury_transactions_customer_id", "customer_id"),
        Index("ix_treasury_transactions_supplier_id", "supplier_id"),
        Index("ix_treasury_transactions_employee_id", "employee_id"),
        CheckConstraint("direction IN ('in', 'out')", name="ck_treasury_transactions_direction"),
        CheckConstraint(
            "movement_type IN ('receipt', 'disbursement', 'expense', 'payroll_payout', 'supplier_payment', 'employee_payment')",
            name="ck_treasury_transactions_movement_type",
        ),
        CheckConstraint("amount != 0", name="ck_treasury_transactions_amount_non_zero"),
        CheckConstraint(
            "(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN supplier_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN employee_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="ck_treasury_transactions_party_cardinality",
        ),
        Index("ix_treasury_transactions_reversed_of_id", "reversed_of_id"),
        CheckConstraint(
            "(CASE WHEN reversed_of_id IS NOT NULL THEN 1 ELSE 0 END) = 0 "
            "OR (CASE WHEN is_reversed THEN 1 ELSE 0 END) = 1",
            name="ck_treasury_transactions_reversal_flag",
        ),
        Index("ix_treasury_transactions_voided", "is_voided"),
    )


__all__ = ["TREASURY_MOVEMENT_TYPES", "TreasuryTransaction"]
