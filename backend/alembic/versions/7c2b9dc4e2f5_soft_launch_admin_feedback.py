"""soft launch admin feedback

Revision ID: 7c2b9dc4e2f5
Revises: c6b1e7e7260d
Create Date: 2025-12-06 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7c2b9dc4e2f5"
down_revision = "c6b1e7e7260d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_soft_launch", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_configs_tenant_id"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_tenant_created_at", "feedback", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_tenant_created_at", table_name="feedback")
    op.drop_table("feedback")
    op.drop_table("tenant_configs")
