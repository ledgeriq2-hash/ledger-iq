"""Add indexes for token hashes to speed lookup."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4c3b9c5c6f1"
down_revision = "0b4a2f6f2cf8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_portal_tokens_token_hash",
        "portal_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_tokens_token_hash", table_name="portal_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
