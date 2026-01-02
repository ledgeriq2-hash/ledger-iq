"""Add POSTED and PARTIAL invoice statuses.

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'POSTED'")
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'PARTIAL'")


def downgrade() -> None:
    # Postgres enum values are not easily removed; no-op.
    return

