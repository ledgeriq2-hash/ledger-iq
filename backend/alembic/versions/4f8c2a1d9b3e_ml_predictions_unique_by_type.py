"""ml_predictions unique by (tenant_id, run_id, prediction_type)

Revision ID: 4f8c2a1d9b3e
Revises: fe12ab34cd56
Create Date: 2025-12-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "4f8c2a1d9b3e"
down_revision = "fe12ab34cd56"
branch_labels = None
depends_on = None


_UQ_OLD = "uq_ml_predictions_tenant_id_run_id"
_UQ_NEW = "uq_ml_predictions_tenant_id_run_id_prediction_type"
_INDEX_LATEST = "ix_ml_predictions_tenant_prediction_created_at"


def _count_null_prediction_type() -> int:
    conn = op.get_bind()
    count = conn.execute(sa.text("SELECT COUNT(*) FROM ml_predictions WHERE prediction_type IS NULL")).scalar_one()
    return int(count or 0)


def _backfill_prediction_type_from_runs() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(
            sa.text(
                """
                UPDATE ml_predictions AS mp
                SET prediction_type = ar.prediction_type
                FROM ai_runs AS ar
                WHERE mp.run_id = ar.id
                  AND mp.prediction_type IS NULL
                  AND ar.prediction_type IS NOT NULL
                """
            )
        )
    else:
        # SQLite-compatible correlated subquery update.
        conn.execute(
            sa.text(
                """
                UPDATE ml_predictions
                SET prediction_type = (
                    SELECT ar.prediction_type
                    FROM ai_runs AS ar
                    WHERE ar.id = ml_predictions.run_id
                )
                WHERE prediction_type IS NULL
                  AND EXISTS (
                    SELECT 1
                    FROM ai_runs AS ar
                    WHERE ar.id = ml_predictions.run_id
                      AND ar.prediction_type IS NOT NULL
                  )
                """
            )
        )


def _assert_no_duplicates_new_key() -> None:
    conn = op.get_bind()
    dup_groups = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM (
              SELECT tenant_id, run_id, prediction_type
              FROM ml_predictions
              GROUP BY tenant_id, run_id, prediction_type
              HAVING COUNT(*) > 1
            ) AS d
            """
        )
    ).scalar_one()
    if int(dup_groups or 0) > 0:
        raise RuntimeError(
            "Migration aborted: duplicate ml_predictions rows exist for the same "
            "(tenant_id, run_id, prediction_type)."
        )


def _has_unique_constraint(table_name: str, name: str) -> bool:
    conn = op.get_bind()
    uniques = inspect(conn).get_unique_constraints(table_name) or []
    return any((u.get("name") or "").lower() == name.lower() for u in uniques)


def _has_index(table_name: str, name: str) -> bool:
    conn = op.get_bind()
    indexes = inspect(conn).get_indexes(table_name) or []
    return any((i.get("name") or "").lower() == name.lower() for i in indexes)


def upgrade() -> None:
    # Ensure prediction_type is populated if any legacy rows exist.
    if _count_null_prediction_type() > 0:
        _backfill_prediction_type_from_runs()
        remaining = _count_null_prediction_type()
        if remaining > 0:
            raise RuntimeError(
                "Migration aborted: ml_predictions.prediction_type contains NULL values and could not be "
                "deterministically backfilled from ai_runs.prediction_type. No default prediction_type is assumed."
            )

    with op.batch_alter_table("ml_predictions") as batch:
        batch.alter_column("prediction_type", existing_type=sa.String(length=50), nullable=False)

        if _has_unique_constraint("ml_predictions", _UQ_OLD):
            batch.drop_constraint(_UQ_OLD, type_="unique")

        _assert_no_duplicates_new_key()
        batch.create_unique_constraint(_UQ_NEW, ["tenant_id", "run_id", "prediction_type"])

    # Support latest prediction queries (tenant + type + created_at ordering).
    if not _has_index("ml_predictions", _INDEX_LATEST):
        op.create_index(
            _INDEX_LATEST,
            "ml_predictions",
            ["tenant_id", "prediction_type", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("ml_predictions") as batch:
        if _has_unique_constraint("ml_predictions", _UQ_NEW):
            batch.drop_constraint(_UQ_NEW, type_="unique")
        batch.create_unique_constraint(_UQ_OLD, ["tenant_id", "run_id"])
