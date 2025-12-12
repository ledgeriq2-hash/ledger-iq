"""soft launch usage and error events

Revision ID: c6b1e7e7260d
Revises: a36d645bff80
Create Date: 2025-12-06 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c6b1e7e7260d"
down_revision = "a36d645bff80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_daily_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("invoices_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payments_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("customers_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_logins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_daily_usage_tenant_date", "tenant_daily_usage", ["tenant_id", "date"], unique=True
    )

    op.create_table(
        "error_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_error_events_tenant_created", "error_events", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_error_events_created_at", "error_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_error_events_created_at", table_name="error_events")
    op.drop_index("ix_error_events_tenant_created", table_name="error_events")
    op.drop_table("error_events")

    op.drop_index("ix_tenant_daily_usage_tenant_date", table_name="tenant_daily_usage")
    op.drop_table("tenant_daily_usage")
