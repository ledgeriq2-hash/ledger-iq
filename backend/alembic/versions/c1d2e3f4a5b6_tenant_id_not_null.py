"""tenant_id not null

Revision ID: c1d2e3f4a5b6
Revises: ab12cd34ef56
Create Date: 2025-12-21
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def _assert_no_null_tenant_ids(table_name: str) -> None:
    conn = op.get_bind()
    count = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id IS NULL")).scalar_one()
    if int(count or 0) > 0:
        raise RuntimeError(f"Migration aborted: {table_name}.tenant_id contains NULL values ({count}).")


def upgrade() -> None:
    for table_name in ("ai_runs", "ml_predictions", "data_snapshots"):
        _assert_no_null_tenant_ids(table_name)

    for table_name in ("ai_runs", "ml_predictions", "data_snapshots"):
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column("tenant_id", existing_type=sa.UUID(), nullable=False)


def downgrade() -> None:
    for table_name in ("ai_runs", "ml_predictions", "data_snapshots"):
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column("tenant_id", existing_type=sa.UUID(), nullable=True)

