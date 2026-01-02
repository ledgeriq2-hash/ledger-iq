"""Add debts and debt payments tables.

Revision ID: a1b2c3d4e5f6
Revises: 4f8c2a1d9b3e
Create Date: 2025-12-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "4f8c2a1d9b3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("(uuid_generate_v4())")),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'open'")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_debts_tenant_id", "debts", ["tenant_id"], unique=False)
    op.create_index("ix_debts_created_at", "debts", ["created_at"], unique=False)
    op.create_index("ix_debts_supplier_id", "debts", ["supplier_id"], unique=False)
    op.create_index("ix_debts_status", "debts", ["status"], unique=False)

    op.create_table(
        "debt_payments",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("(uuid_generate_v4())")),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("debt_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_debt_payments_tenant_id", "debt_payments", ["tenant_id"], unique=False)
    op.create_index("ix_debt_payments_created_at", "debt_payments", ["created_at"], unique=False)
    op.create_index("ix_debt_payments_debt_id", "debt_payments", ["debt_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_debt_payments_debt_id", table_name="debt_payments")
    op.drop_index("ix_debt_payments_created_at", table_name="debt_payments")
    op.drop_index("ix_debt_payments_tenant_id", table_name="debt_payments")
    op.drop_table("debt_payments")

    op.drop_index("ix_debts_status", table_name="debts")
    op.drop_index("ix_debts_supplier_id", table_name="debts")
    op.drop_index("ix_debts_created_at", table_name="debts")
    op.drop_index("ix_debts_tenant_id", table_name="debts")
    op.drop_table("debts")
