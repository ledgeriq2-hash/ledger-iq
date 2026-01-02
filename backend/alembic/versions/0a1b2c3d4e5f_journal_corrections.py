"""Add journal correction metadata and treasury linking.

Revision ID: 0a1b2c3d4e5f
Revises: e1f2a3b4c5d6
Create Date: 2025-12-31 12:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0a1b2c3d4e5f"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("adjustment_reason", sa.String(length=255), nullable=True))
    op.add_column(
        "journal_entries",
        sa.Column(
            "adjusted_of_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("journal_entries", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column(
        "journal_entries",
        sa.Column(
            "treasury_transaction_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("treasury_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("journal_entries", sa.Column("is_reversed", sa.Boolean(), server_default="FALSE", nullable=False))
    op.add_column("journal_entries", sa.Column("is_voided", sa.Boolean(), server_default="FALSE", nullable=False))
    op.add_column("journal_entries", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "journal_entries",
        sa.Column(
            "voided_by_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("journal_entries", sa.Column("voided_reason", sa.String(length=255), nullable=True))
    op.create_index("ix_journal_entries_idempotency_key", "journal_entries", ["idempotency_key"])
    op.create_index("ix_journal_entries_treasury_transaction_id", "journal_entries", ["treasury_transaction_id"])
    op.create_unique_constraint("uq_journal_entries_reversed_of_id", "journal_entries", ["reversed_of_id"])
    op.create_unique_constraint(
        "uq_journal_entries_adjustment",
        "journal_entries",
        ["adjusted_of_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_journal_entries_adjustment", "journal_entries", type_="unique")
    op.drop_constraint("uq_journal_entries_reversed_of_id", "journal_entries", type_="unique")
    op.drop_index("ix_journal_entries_treasury_transaction_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_idempotency_key", table_name="journal_entries")
    op.drop_column("journal_entries", "voided_reason")
    op.drop_column("journal_entries", "voided_by_user_id")
    op.drop_column("journal_entries", "voided_at")
    op.drop_column("journal_entries", "is_voided")
    op.drop_column("journal_entries", "is_reversed")
    op.drop_column("journal_entries", "treasury_transaction_id")
    op.drop_column("journal_entries", "idempotency_key")
    op.drop_column("journal_entries", "adjusted_of_id")
    op.drop_column("journal_entries", "adjustment_reason")
