"""Add treasuries and treasury_transactions tables.

Revision ID: e7f8a9b0c1d2
Revises: b1c2d3e4f5a6
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c1d2"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.create_index("ix_treasuries_tenant_id", "treasuries", ["tenant_id"], unique=False)
    op.create_index("ix_treasuries_created_at", "treasuries", ["created_at"], unique=False)

    op.create_table(
        "treasury_transactions",
        sa.Column("treasury_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("reference_type", sa.String(length=100), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["treasury_id"], ["treasuries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_transactions_treasury_id", "treasury_transactions", ["treasury_id"], unique=False)
    op.create_index("ix_treasury_transactions_tenant_id", "treasury_transactions", ["tenant_id"], unique=False)
    op.create_index("ix_treasury_transactions_created_at", "treasury_transactions", ["created_at"], unique=False)
    op.create_index(
        "ix_treasury_transactions_tenant_created_at",
        "treasury_transactions",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_transactions_reference",
        "treasury_transactions",
        ["reference_type", "reference_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_treasury_transactions_reference", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_tenant_created_at", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_created_at", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_tenant_id", table_name="treasury_transactions")
    op.drop_index("ix_treasury_transactions_treasury_id", table_name="treasury_transactions")
    op.drop_table("treasury_transactions")

    op.drop_index("ix_treasuries_created_at", table_name="treasuries")
    op.drop_index("ix_treasuries_tenant_id", table_name="treasuries")
    op.drop_table("treasuries")

