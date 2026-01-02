"""add journal entry currency fields"""

from alembic import op
import sqlalchemy as sa


revision = "b7f0e1c2d3a4"
down_revision = "fe12ab34cd56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("journal_entries") as batch:
        batch.add_column(sa.Column("currency_code", sa.String(length=10), nullable=True))
        batch.add_column(sa.Column("fx_rate", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("source_module", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("source_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("reversed_of_id", sa.UUID(), nullable=True))
        batch.create_foreign_key(
            "fk_journal_entries_reversed_of",
            "journal_entries",
            ["reversed_of_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_journal_entries_source_module", ["source_module"])


def downgrade() -> None:
    with op.batch_alter_table("journal_entries") as batch:
        batch.drop_index("ix_journal_entries_source_module")
        batch.drop_constraint("fk_journal_entries_reversed_of", type_="foreignkey")
        batch.drop_column("reversed_of_id")
        batch.drop_column("source_id")
        batch.drop_column("source_module")
        batch.drop_column("fx_rate")
        batch.drop_column("currency_code")
