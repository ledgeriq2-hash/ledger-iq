"""add data_snapshots

Revision ID: ab12cd34ef56
Revises: d323cb55944c
Create Date: 2025-12-21
"""

from alembic import op
import sqlalchemy as sa


revision = "ab12cd34ef56"
down_revision = "d323cb55944c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_snapshots",
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("granularity", sa.String(length=50), nullable=True),
        sa.Column("filters_hash", sa.String(length=255), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "source", "filters_hash", name="uq_data_snapshots_tenant_source_filters_hash"),
    )
    op.create_index(
        "ix_data_snapshots_tenant_source_created_at",
        "data_snapshots",
        ["tenant_id", "source", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_data_snapshots_tenant_source_created_at", table_name="data_snapshots")
    op.drop_table("data_snapshots")

