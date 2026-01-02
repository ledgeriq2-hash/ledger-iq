"""add payments event_date index"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "payments", "event_date"):
        with op.batch_alter_table("payments") as batch:
            batch.add_column(sa.Column("event_date", sa.Date(), nullable=True, server_default=sa.text("(CURRENT_DATE)")))

    op.execute(
        "UPDATE payments SET event_date = COALESCE(CAST(paid_at AS DATE), CAST(created_at AS DATE), CURRENT_DATE) "
        "WHERE event_date IS NULL"
    )

    with op.batch_alter_table("payments") as batch:
        batch.alter_column("event_date", existing_type=sa.Date(), nullable=False)
        batch.alter_column("event_date", existing_type=sa.Date(), server_default=sa.text("(CURRENT_DATE)"))

    inspector = sa.inspect(bind)
    index_name = "ix_payments_tenant_event_date"
    if not _index_exists(inspector, "payments", index_name):
        op.create_index(index_name, "payments", ["tenant_id", "event_date"])


def downgrade() -> None:
    op.drop_index("ix_payments_tenant_event_date", table_name="payments")
