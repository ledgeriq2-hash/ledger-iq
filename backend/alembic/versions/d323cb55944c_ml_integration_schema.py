"""ml integration schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d323cb55944c"
down_revision = "3b2c1d0e9f8a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    for table_name, idx_name, fill_sql in (
        ("invoices", "ix_invoices_event_date", 'UPDATE invoices SET event_date = issue_date WHERE event_date IS NULL'),
        ("expenses", "ix_expenses_event_date", 'UPDATE expenses SET event_date = expense_date WHERE event_date IS NULL'),
        ("payments", "ix_payments_event_date", "UPDATE payments SET event_date = COALESCE(CAST(paid_at AS DATE), CAST(created_at AS DATE)) WHERE event_date IS NULL"),
        ("treasury_transactions", "ix_treasury_transactions_event_date", "UPDATE treasury_transactions SET event_date = CAST(created_at AS DATE) WHERE event_date IS NULL"),
        ("journal_entries", "ix_journal_entries_event_date", 'UPDATE journal_entries SET event_date = "date" WHERE event_date IS NULL'),
        ("stock_movements", "ix_stock_movements_event_date", "UPDATE stock_movements SET event_date = CAST(created_at AS DATE) WHERE event_date IS NULL"),
    ):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("event_date", sa.Date(), nullable=True, server_default=sa.text("(CURRENT_DATE)")))
            batch.create_index(idx_name, ["event_date"])

        op.execute(fill_sql)

        with op.batch_alter_table(table_name) as batch:
            batch.alter_column("event_date", existing_type=sa.Date(), nullable=False)

    with op.batch_alter_table("ai_runs") as batch:
        batch.add_column(sa.Column("prediction_type", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("model_version", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("data_snapshot_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("params", json_type, nullable=True))
        batch.add_column(sa.Column("metrics", json_type, nullable=True))
        batch.add_column(sa.Column("trigger", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("requested_by", sa.UUID(), nullable=True))

        batch.create_foreign_key(
            "fk_ai_runs_requested_by_users",
            "users",
            ["requested_by"],
            ["id"],
            ondelete="SET NULL",
        )

        batch.create_index("ix_ai_runs_prediction_type", ["prediction_type"])
        batch.create_index("ix_ai_runs_model_version", ["model_version"])
        batch.create_index("ix_ai_runs_data_snapshot_id", ["data_snapshot_id"])
        batch.create_index("ix_ai_runs_requested_by", ["requested_by"])

    op.create_table(
        "ml_predictions",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("prediction_type", sa.String(length=50), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("granularity", sa.String(length=20), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("series", json_type, nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ai_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_predictions_tenant_id", "ml_predictions", ["tenant_id"], unique=False)
    op.create_index("ix_ml_predictions_created_at", "ml_predictions", ["created_at"], unique=False)
    op.create_index("ix_ml_predictions_tenant_created_at", "ml_predictions", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_ml_predictions_run_id", "ml_predictions", ["run_id"], unique=False)
    op.create_index("ix_ml_predictions_prediction_type", "ml_predictions", ["prediction_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ml_predictions_prediction_type", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_run_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_tenant_created_at", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_created_at", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_tenant_id", table_name="ml_predictions")
    op.drop_table("ml_predictions")

    with op.batch_alter_table("ai_runs") as batch:
        batch.drop_index("ix_ai_runs_requested_by")
        batch.drop_index("ix_ai_runs_data_snapshot_id")
        batch.drop_index("ix_ai_runs_model_version")
        batch.drop_index("ix_ai_runs_prediction_type")

        batch.drop_constraint("fk_ai_runs_requested_by_users", type_="foreignkey")

        batch.drop_column("requested_by")
        batch.drop_column("trigger")
        batch.drop_column("metrics")
        batch.drop_column("params")
        batch.drop_column("data_snapshot_id")
        batch.drop_column("model_version")
        batch.drop_column("prediction_type")

    for table_name, idx_name in (
        ("stock_movements", "ix_stock_movements_event_date"),
        ("journal_entries", "ix_journal_entries_event_date"),
        ("treasury_transactions", "ix_treasury_transactions_event_date"),
        ("payments", "ix_payments_event_date"),
        ("expenses", "ix_expenses_event_date"),
        ("invoices", "ix_invoices_event_date"),
    ):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_index(idx_name)
            batch.drop_column("event_date")
