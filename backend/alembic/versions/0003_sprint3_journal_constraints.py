"""Add reversal uniqueness constraint for journal entries.

Revision ID: 0003_sprint3_journal_constraints
Revises: 0002_coa_ledger
Create Date: 2026-01-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_sprint3_journal_constraints"
down_revision = "0002_coa_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ux_journal_entries_reversed_of_id",
        "journal_entries",
        ["reversed_of_id"],
        unique=True,
        postgresql_where=sa.text("reversed_of_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_journal_entries_reversed_of_id", table_name="journal_entries")
