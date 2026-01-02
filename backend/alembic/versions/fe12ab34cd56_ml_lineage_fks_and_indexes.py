"""ML lineage FKs and indexes

Revision ID: fe12ab34cd56
Revises: d7e8f9a0b1c2
Create Date: 2025-12-22
"""

from alembic import op
import sqlalchemy as sa


revision = "fe12ab34cd56"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Backfill data_snapshots for any existing ai_runs that already reference data_snapshot_id
    # so we can safely add a foreign key without deleting data.
    conn.execute(
        sa.text(
            """
            INSERT INTO data_snapshots (
              id, tenant_id, source, from_date, to_date, granularity, filters_hash, rows_count, checksum, created_at
            )
            SELECT
              ar.data_snapshot_id,
              ar.tenant_id,
              'ml_ingest',
              NULL,
              NULL,
              NULL,
              CAST(ar.data_snapshot_id AS TEXT),
              NULL,
              NULL,
              ar.created_at
            FROM (
              SELECT DISTINCT tenant_id, data_snapshot_id, created_at
              FROM ai_runs
              WHERE data_snapshot_id IS NOT NULL
            ) AS ar
            LEFT JOIN data_snapshots ds ON ds.id = ar.data_snapshot_id
            WHERE ds.id IS NULL
            """
        )
    )

    with op.batch_alter_table("ai_runs") as batch:
        batch.create_foreign_key(
            "fk_ai_runs_data_snapshot_id_data_snapshots",
            "data_snapshots",
            ["data_snapshot_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_ai_runs_tenant_prediction_model_created_at",
        "ai_runs",
        ["tenant_id", "prediction_type", "model_version", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ml_predictions_tenant_prediction_created_at",
        "ml_predictions",
        ["tenant_id", "prediction_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ml_predictions_tenant_prediction_created_at", table_name="ml_predictions")
    op.drop_index("ix_ai_runs_tenant_prediction_model_created_at", table_name="ai_runs")
    with op.batch_alter_table("ai_runs") as batch:
        batch.drop_constraint("fk_ai_runs_data_snapshot_id_data_snapshots", type_="foreignkey")

