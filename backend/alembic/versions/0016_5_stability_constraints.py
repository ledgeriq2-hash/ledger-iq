"""Sprint 16.5 stability constraints."""

from alembic import op
import sqlalchemy as sa


revision = "0016_5_stability_constraints"
down_revision = "0011_sprint15_ai_runs_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY client_id, model_name, model_version, dataset_fingerprint, scenario, payload_hash
                        ORDER BY created_at DESC, id DESC
                    ) AS rn
                FROM ai_runs
            )
            DELETE FROM ai_runs
            WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
            """
        )
    )
    inspector = sa.inspect(conn)
    existing = {idx["name"] for idx in inspector.get_indexes("ai_runs")}
    if "ux_ai_runs_client_model_version_dataset_scenario_payload_hash" not in existing:
        op.create_index(
            "ux_ai_runs_client_model_version_dataset_scenario_payload_hash",
            "ai_runs",
            ["client_id", "model_name", "model_version", "dataset_fingerprint", "scenario", "payload_hash"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(
        "ux_ai_runs_client_model_version_dataset_scenario_payload_hash",
        table_name="ai_runs",
    )
