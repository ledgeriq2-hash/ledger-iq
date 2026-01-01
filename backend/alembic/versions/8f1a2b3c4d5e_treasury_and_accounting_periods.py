"""Add treasury tables and accounting period locks.

Revision ID: 8f1a2b3c4d5e
Revises: 6e7f8a9b0c1d
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "8f1a2b3c4d5e"
down_revision = "6e7f8a9b0c1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_period_locks",
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "locked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("locked_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_period_locks_tenant_id", "accounting_period_locks", ["tenant_id"])
    op.create_index("ix_accounting_period_locks_created_at", "accounting_period_locks", ["created_at"])
    op.create_index(
        "ix_accounting_period_locks_tenant_start_end",
        "accounting_period_locks",
        ["tenant_id", "start_date", "end_date"],
    )

    op.create_table(
        "treasuries",
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasuries_tenant_id", "treasuries", ["tenant_id"])
    op.create_index("ix_treasuries_created_at", "treasuries", ["created_at"])

    op.create_table(
        "treasury_transactions",
        sa.Column("treasury_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("journal_entry_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("employee_id", sa.UUID(), nullable=True),
        sa.Column("reversed_of_id", sa.UUID(), nullable=True),
        sa.Column("is_reversed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("is_voided", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", sa.UUID(), nullable=True),
        sa.Column("voided_reason", sa.String(length=255), nullable=True),
        sa.Column("reference_type", sa.String(length=100), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("event_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["treasury_id"], ["treasuries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversed_of_id"], ["treasury_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_transactions_tenant_id", "treasury_transactions", ["tenant_id"])
    op.create_index("ix_treasury_transactions_created_at", "treasury_transactions", ["created_at"])
    op.create_index(
        "ix_treasury_transactions_tenant_created_at",
        "treasury_transactions",
        ["tenant_id", "created_at"],
    )
    op.create_index("ix_treasury_transactions_event_date", "treasury_transactions", ["event_date"])
    op.create_index(
        "ix_treasury_transactions_reference",
        "treasury_transactions",
        ["reference_type", "reference_id"],
    )
    op.create_index("ix_treasury_transactions_treasury_id", "treasury_transactions", ["treasury_id"])
    op.create_index("ix_treasury_transactions_journal_entry_id", "treasury_transactions", ["journal_entry_id"])
    op.create_index("ix_treasury_transactions_movement_type", "treasury_transactions", ["movement_type"])
    op.create_index("ix_treasury_transactions_customer_id", "treasury_transactions", ["customer_id"])
    op.create_index("ix_treasury_transactions_supplier_id", "treasury_transactions", ["supplier_id"])
    op.create_index("ix_treasury_transactions_employee_id", "treasury_transactions", ["employee_id"])
    op.create_index("ix_treasury_transactions_reversed_of_id", "treasury_transactions", ["reversed_of_id"])
    op.create_index("ix_treasury_transactions_voided", "treasury_transactions", ["is_voided"])

    op.create_check_constraint(
        "ck_treasury_transactions_direction",
        "treasury_transactions",
        "direction IN ('in', 'out')",
    )
    op.create_check_constraint(
        "ck_treasury_transactions_movement_type",
        "treasury_transactions",
        "movement_type IN ('receipt', 'disbursement', 'expense', 'payroll_payout', 'supplier_payment', 'employee_payment')",
    )
    op.create_check_constraint(
        "ck_treasury_transactions_amount_non_zero",
        "treasury_transactions",
        "amount != 0",
    )
    op.create_check_constraint(
        "ck_treasury_transactions_party_cardinality",
        "treasury_transactions",
        "(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN supplier_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN employee_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
    )
    op.create_check_constraint(
        "ck_treasury_transactions_reversal_flag",
        "treasury_transactions",
        "(CASE WHEN reversed_of_id IS NOT NULL THEN 1 ELSE 0 END) = 0 "
        "OR (CASE WHEN is_reversed THEN 1 ELSE 0 END) = 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_treasury_transactions_reversal_flag", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_party_cardinality", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_amount_non_zero", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_movement_type", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_direction", "treasury_transactions", type_="check")

    op.drop_index("ix_treasury_transactions_voided", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_reversed_of_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_employee_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_supplier_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_customer_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_movement_type", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_journal_entry_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_treasury_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_reference", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_event_date", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_tenant_created_at", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_created_at", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_tenant_id", table_name="treasury_transactions")
    op.drop_table("treasury_transactions")

    op.drop_index("ix_treasuries_created_at", table_name="treasuries")
    op.drop_index("ix_treasuries_tenant_id", table_name="treasuries")
    op.drop_table("treasuries")

    op.drop_index("ix_accounting_period_locks_tenant_start_end", table_name="accounting_period_locks")
    op.drop_index("ix_accounting_period_locks_created_at", table_name="accounting_period_locks")
    op.drop_index("ix_accounting_period_locks_tenant_id", table_name="accounting_period_locks")
    op.drop_table("accounting_period_locks")
