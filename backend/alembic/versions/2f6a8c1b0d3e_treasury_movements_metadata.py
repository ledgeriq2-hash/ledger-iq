"""Add metadata for treasury movements.

Revision ID: 2f6a8c1b0d3e
Revises: 0a1b2c3d4e5f
Create Date: 2025-12-31 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "2f6a8c1b0d3e"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "treasury_transactions",
        sa.Column("movement_type", sa.String(length=30), nullable=False, server_default="disbursement"),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("journal_entry_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("customer_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("supplier_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("employee_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("reversed_of_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("is_reversed", sa.Boolean(), nullable=False, server_default="FALSE"),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("is_voided", sa.Boolean(), nullable=False, server_default="FALSE"),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("voided_by_user_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "treasury_transactions",
        sa.Column("voided_reason", sa.String(length=255), nullable=True),
    )

    op.create_index("ix_treasury_transactions_journal_entry_id", "treasury_transactions", ["journal_entry_id"])
    op.create_index("ix_treasury_transactions_movement_type", "treasury_transactions", ["movement_type"])
    op.create_index("ix_treasury_transactions_customer_id", "treasury_transactions", ["customer_id"])
    op.create_index("ix_treasury_transactions_supplier_id", "treasury_transactions", ["supplier_id"])
    op.create_index("ix_treasury_transactions_employee_id", "treasury_transactions", ["employee_id"])
    op.create_index("ix_treasury_transactions_reversed_of_id", "treasury_transactions", ["reversed_of_id"])
    op.create_index("ix_treasury_transactions_voided", "treasury_transactions", ["is_voided"])

    op.create_foreign_key(
        "fk_treasury_transactions_journal_entry_id",
        "treasury_transactions",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_treasury_transactions_customer_id", "treasury_transactions", "customers", ["customer_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_treasury_transactions_supplier_id", "treasury_transactions", "suppliers", ["supplier_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_treasury_transactions_employee_id", "treasury_transactions", "employees", ["employee_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_treasury_transactions_reversed_of_id",
        "treasury_transactions",
        "treasury_transactions",
        ["reversed_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_treasury_transactions_voided_by_user_id",
        "treasury_transactions",
        "users",
        ["voided_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

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

    op.create_unique_constraint(
        "uq_treasury_transactions_reversed_of_id", "treasury_transactions", ["reversed_of_id"]
    )

    bind = op.get_bind()
    has_rows = bind.execute(sa.text("SELECT 1 FROM treasury_transactions LIMIT 1")).first()
    if not has_rows:
        op.alter_column("treasury_transactions", "journal_entry_id", nullable=False)

    op.alter_column("treasury_transactions", "movement_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_treasury_transactions_reversed_of_id", "treasury_transactions", type_="unique")
    op.drop_constraint("ck_treasury_transactions_reversal_flag", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_party_cardinality", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_amount_non_zero", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_movement_type", "treasury_transactions", type_="check")
    op.drop_constraint("ck_treasury_transactions_direction", "treasury_transactions", type_="check")

    op.drop_constraint("fk_treasury_transactions_voided_by_user_id", "treasury_transactions", type_="foreignkey")
    op.drop_constraint("fk_treasury_transactions_reversed_of_id", "treasury_transactions", type_="foreignkey")
    op.drop_constraint("fk_treasury_transactions_employee_id", "treasury_transactions", type_="foreignkey")
    op.drop_constraint("fk_treasury_transactions_supplier_id", "treasury_transactions", type_="foreignkey")
    op.drop_constraint("fk_treasury_transactions_customer_id", "treasury_transactions", type_="foreignkey")
    op.drop_constraint("fk_treasury_transactions_journal_entry_id", "treasury_transactions", type_="foreignkey")

    op.drop_index("ix_treasury_transactions_voided", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_reversed_of_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_employee_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_supplier_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_customer_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_movement_type", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_journal_entry_id", table_name="treasury_transactions")

    op.drop_column("treasury_transactions", "voided_reason")
    op.drop_column("treasury_transactions", "voided_by_user_id")
    op.drop_column("treasury_transactions", "voided_at")
    op.drop_column("treasury_transactions", "is_voided")
    op.drop_column("treasury_transactions", "is_reversed")
    op.drop_column("treasury_transactions", "reversed_of_id")
    op.drop_column("treasury_transactions", "employee_id")
    op.drop_column("treasury_transactions", "supplier_id")
    op.drop_column("treasury_transactions", "customer_id")
    op.drop_column("treasury_transactions", "journal_entry_id")
    op.drop_column("treasury_transactions", "movement_type")
