"""Add accounting_period_locks table.

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a9b8c7d6e5f4"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_period_locks",
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("locked_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_period_locks_tenant_id", "accounting_period_locks", ["tenant_id"], unique=False)
    op.create_index("ix_accounting_period_locks_created_at", "accounting_period_locks", ["created_at"], unique=False)
    op.create_index(
        "ix_accounting_period_locks_tenant_start_end",
        "accounting_period_locks",
        ["tenant_id", "start_date", "end_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_accounting_period_locks_tenant_start_end", table_name="accounting_period_locks")
    op.drop_index("ix_accounting_period_locks_created_at", table_name="accounting_period_locks")
    op.drop_index("ix_accounting_period_locks_tenant_id", table_name="accounting_period_locks")
    op.drop_table("accounting_period_locks")

