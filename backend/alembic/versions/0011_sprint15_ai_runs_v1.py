"""Sprint 15.1 AI runs v1 schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_sprint15_ai_runs_v1"
down_revision = "0010_sprint14_inventory_link"
branch_labels = None
depends_on = None


def _create_ai_runs_table() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("dataset_fingerprint", sa.Text(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("scenario", sa.Text(), server_default=sa.text("'baseline'"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'approved'"), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Text(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("superseded_by_run_id", sa.UUID(), nullable=True),
        sa.CheckConstraint("status IN ('approved', 'revoked')", name="ck_ai_runs_status"),
        sa.CheckConstraint("char_length(payload_hash) = 64", name="ck_ai_runs_payload_hash_len"),
        sa.CheckConstraint(
            "status <> 'revoked' OR revoked_at IS NOT NULL",
            name="ck_ai_runs_revoked_requires_timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_run_id"],
            ["ai_runs.id"],
            name="fk_ai_runs_superseded_by_run_id_ai_runs",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_runs_client_created_at",
        "ai_runs",
        ["client_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_ai_runs_client_status", "ai_runs", ["client_id", "status"], unique=False)
    op.create_index("ix_ai_runs_client_scenario", "ai_runs", ["client_id", "scenario"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ai_runs"):
        _create_ai_runs_table()
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ai_runs")}
    for index_name in (
        "ix_ai_runs_tenant_prediction_model_created_at",
        "ix_ai_runs_tenant_created_at",
        "ix_ai_runs_tenant_id",
        "ix_ai_runs_created_at",
        "ix_ai_runs_status",
        "ix_ai_runs_prediction_type",
        "ix_ai_runs_model_version",
        "ix_ai_runs_data_snapshot_id",
        "ix_ai_runs_requested_by",
    ):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="ai_runs")

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("ai_runs")}
    for fk_name in (
        "fk_ai_runs_requested_by_users",
        "fk_ai_runs_data_snapshot_id_data_snapshots",
    ):
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, "ai_runs", type_="foreignkey")

    existing_columns = {col["name"] for col in inspector.get_columns("ai_runs")}
    with op.batch_alter_table("ai_runs") as batch:
        for column_name in (
            "tenant_id",
            "updated_at",
            "status",
            "started_at",
            "finished_at",
            "error",
            "prediction_type",
            "model_version",
            "data_snapshot_id",
            "params",
            "metrics",
            "trigger",
            "requested_by",
        ):
            if column_name in existing_columns:
                batch.drop_column(column_name)

        batch.add_column(sa.Column("client_id", sa.UUID(), nullable=False))
        batch.add_column(sa.Column("schema_version", sa.Text(), nullable=False))
        batch.add_column(sa.Column("model_name", sa.Text(), nullable=False))
        batch.add_column(sa.Column("model_version", sa.Text(), nullable=False))
        batch.add_column(sa.Column("dataset_fingerprint", sa.Text(), nullable=False))
        batch.add_column(sa.Column("date_from", sa.Date(), nullable=True))
        batch.add_column(sa.Column("date_to", sa.Date(), nullable=True))
        batch.add_column(sa.Column("scenario", sa.Text(), server_default=sa.text("'baseline'"), nullable=False))
        batch.add_column(sa.Column("status", sa.String(length=20), server_default=sa.text("'approved'"), nullable=False))
        batch.add_column(sa.Column("payload_hash", sa.String(length=64), nullable=False))
        batch.add_column(sa.Column("payload_json", postgresql.JSONB(), nullable=False))
        batch.add_column(sa.Column("signature", sa.Text(), nullable=True))
        batch.add_column(sa.Column("created_by", sa.Text(), nullable=True))
        batch.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("revoked_by", sa.Text(), nullable=True))
        batch.add_column(sa.Column("revoke_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("superseded_by_run_id", sa.UUID(), nullable=True))

        batch.create_foreign_key(
            "fk_ai_runs_superseded_by_run_id_ai_runs",
            "ai_runs",
            ["superseded_by_run_id"],
            ["id"],
        )
        batch.create_check_constraint("ck_ai_runs_status", "status IN ('approved', 'revoked')")
        batch.create_check_constraint("ck_ai_runs_payload_hash_len", "char_length(payload_hash) = 64")
        batch.create_check_constraint(
            "ck_ai_runs_revoked_requires_timestamp",
            "status <> 'revoked' OR revoked_at IS NOT NULL",
        )

    op.create_index(
        "ix_ai_runs_client_created_at",
        "ai_runs",
        ["client_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_ai_runs_client_status", "ai_runs", ["client_id", "status"], unique=False)
    op.create_index("ix_ai_runs_client_scenario", "ai_runs", ["client_id", "scenario"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ai_runs"):
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ai_runs")}
    for index_name in (
        "ix_ai_runs_client_created_at",
        "ix_ai_runs_client_status",
        "ix_ai_runs_client_scenario",
    ):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="ai_runs")

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("ai_runs")}
    existing_checks = {ck["name"] for ck in inspector.get_check_constraints("ai_runs")}
    existing_columns = {col["name"] for col in inspector.get_columns("ai_runs")}

    with op.batch_alter_table("ai_runs") as batch:
        for constraint_name in (
            "ck_ai_runs_revoked_requires_timestamp",
            "ck_ai_runs_payload_hash_len",
            "ck_ai_runs_status",
        ):
            if constraint_name in existing_checks:
                batch.drop_constraint(constraint_name, type_="check")

        for fk_name in ("fk_ai_runs_superseded_by_run_id_ai_runs",):
            if fk_name in existing_fks:
                batch.drop_constraint(fk_name, type_="foreignkey")

        for column_name in (
            "client_id",
            "schema_version",
            "model_name",
            "model_version",
            "dataset_fingerprint",
            "date_from",
            "date_to",
            "scenario",
            "status",
            "payload_hash",
            "payload_json",
            "signature",
            "created_by",
            "revoked_at",
            "revoked_by",
            "revoke_reason",
            "superseded_by_run_id",
        ):
            if column_name in existing_columns:
                batch.drop_column(column_name)

        batch.add_column(sa.Column("tenant_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False))
        batch.add_column(sa.Column("status", sa.String(length=20), server_default="SUCCESS", nullable=False))
        batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=False))
        batch.add_column(sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("error", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("prediction_type", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("model_version", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("data_snapshot_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("params", postgresql.JSONB(), nullable=True))
        batch.add_column(sa.Column("metrics", postgresql.JSONB(), nullable=True))
        batch.add_column(sa.Column("trigger", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("requested_by", sa.UUID(), nullable=True))

        batch.create_foreign_key(
            "fk_ai_runs_requested_by_users",
            "users",
            ["requested_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_ai_runs_data_snapshot_id_data_snapshots",
            "data_snapshots",
            ["data_snapshot_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index("ix_ai_runs_tenant_id", "ai_runs", ["tenant_id"], unique=False)
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"], unique=False)
    op.create_index("ix_ai_runs_tenant_created_at", "ai_runs", ["tenant_id", "created_at"], unique=False)
    op.create_index(
        "ix_ai_runs_tenant_prediction_model_created_at",
        "ai_runs",
        ["tenant_id", "prediction_type", "model_version", "created_at"],
        unique=False,
    )
    op.create_index("ix_ai_runs_status", "ai_runs", ["status"], unique=False)
    op.create_index("ix_ai_runs_prediction_type", "ai_runs", ["prediction_type"], unique=False)
    op.create_index("ix_ai_runs_model_version", "ai_runs", ["model_version"], unique=False)
    op.create_index("ix_ai_runs_data_snapshot_id", "ai_runs", ["data_snapshot_id"], unique=False)
    op.create_index("ix_ai_runs_requested_by", "ai_runs", ["requested_by"], unique=False)
