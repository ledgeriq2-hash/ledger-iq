"""Merge heads: ai_runs_and_insights + accounting_period_locks.

Revision ID: 3b2c1d0e9f8a
Revises: 0f2c6a1b9d3e, a9b8c7d6e5f4
Create Date: 2025-12-18 00:00:00.000000
"""

from alembic import op

revision = "3b2c1d0e9f8a"
down_revision = ("0f2c6a1b9d3e", "a9b8c7d6e5f4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT 1")


def downgrade() -> None:
    op.execute("SELECT 1")

