"""Add LedgerEntry fields to journal_entry_lines.

Revision ID: b1c2d3e4f5a6
Revises: 35c9b7e62f1a, 7c2b9dc4e2f5, 8c1a2e3f4d5b
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = ("35c9b7e62f1a", "7c2b9dc4e2f5", "8c1a2e3f4d5b")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("journal_entry_lines") as batch:
        batch.add_column(sa.Column("entity_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("entity_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("reference_type", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("reference_id", sa.UUID(), nullable=True))

        batch.create_index("ix_journal_entry_lines_tenant_created_at", ["tenant_id", "created_at"])
        batch.create_index("ix_journal_entry_lines_reference", ["reference_type", "reference_id"])


def downgrade() -> None:
    with op.batch_alter_table("journal_entry_lines") as batch:
        batch.drop_index("ix_journal_entry_lines_reference")
        batch.drop_index("ix_journal_entry_lines_tenant_created_at")

        batch.drop_column("reference_id")
        batch.drop_column("reference_type")
        batch.drop_column("entity_id")
        batch.drop_column("entity_type")

