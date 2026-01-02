"""unique ml_predictions

Revision ID: d7e8f9a0b1c2
Revises: c1d2e3f4a5b6
Create Date: 2025-12-21
"""

from alembic import op
import sqlalchemy as sa


revision = "d7e8f9a0b1c2"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


_UQ_NAME = "uq_ml_predictions_tenant_id_run_id"


def _assert_no_duplicates() -> None:
    conn = op.get_bind()
    dup_groups = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM (
              SELECT tenant_id, run_id
              FROM ml_predictions
              GROUP BY tenant_id, run_id
              HAVING COUNT(*) > 1
            ) AS d
            """
        )
    ).scalar_one()
    if int(dup_groups or 0) > 0:
        raise RuntimeError(f"Migration aborted: duplicate ml_predictions rows exist for the same (tenant_id, run_id) ({dup_groups} groups).")


def upgrade() -> None:
    _assert_no_duplicates()
    op.create_unique_constraint(_UQ_NAME, "ml_predictions", ["tenant_id", "run_id"])


def downgrade() -> None:
    op.drop_constraint(_UQ_NAME, "ml_predictions", type_="unique")

