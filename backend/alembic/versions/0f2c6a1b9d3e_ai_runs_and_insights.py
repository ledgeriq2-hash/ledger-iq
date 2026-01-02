"""Add ai_runs and ai_insights tables.

Revision ID: 0f2c6a1b9d3e
Revises: f1a2b3c4d5e6
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0f2c6a1b9d3e"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("status", sa.String(length=20), server_default="SUCCESS", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_runs_tenant_id", "ai_runs", ["tenant_id"], unique=False)
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"], unique=False)
    op.create_index("ix_ai_runs_tenant_created_at", "ai_runs", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_ai_runs_status", "ai_runs", ["status"], unique=False)

    op.create_table(
        "ai_insights",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), server_default="0", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("reference_type", sa.String(length=100), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ai_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_insights_run_id", "ai_insights", ["run_id"], unique=False)
    op.create_index("ix_ai_insights_tenant_id", "ai_insights", ["tenant_id"], unique=False)
    op.create_index("ix_ai_insights_created_at", "ai_insights", ["created_at"], unique=False)
    op.create_index("ix_ai_insights_tenant_created_at", "ai_insights", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_ai_insights_type", "ai_insights", ["type"], unique=False)
    op.create_index("ix_ai_insights_severity", "ai_insights", ["severity"], unique=False)
    op.create_index("ix_ai_insights_confidence", "ai_insights", ["confidence"], unique=False)
    op.create_index("ix_ai_insights_reference", "ai_insights", ["reference_type", "reference_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_insights_reference", table_name="ai_insights")
    op.drop_index("ix_ai_insights_confidence", table_name="ai_insights")
    op.drop_index("ix_ai_insights_severity", table_name="ai_insights")
    op.drop_index("ix_ai_insights_type", table_name="ai_insights")
    op.drop_index("ix_ai_insights_tenant_created_at", table_name="ai_insights")
    op.drop_index("ix_ai_insights_created_at", table_name="ai_insights")
    op.drop_index("ix_ai_insights_tenant_id", table_name="ai_insights")
    op.drop_index("ix_ai_insights_run_id", table_name="ai_insights")
    op.drop_table("ai_insights")

    op.drop_index("ix_ai_runs_status", table_name="ai_runs")
    op.drop_index("ix_ai_runs_tenant_created_at", table_name="ai_runs")
    op.drop_index("ix_ai_runs_created_at", table_name="ai_runs")
    op.drop_index("ix_ai_runs_tenant_id", table_name="ai_runs")
    op.drop_table("ai_runs")

