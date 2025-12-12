"""security mfa and sessions

Revision ID: 35c9b7e62f1a
Revises: 0b4a2f6f2cf8
Create Date: 2025-12-07 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "35c9b7e62f1a"
down_revision = "0b4a2f6f2cf8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=64), nullable=True))

    op.add_column("refresh_tokens", sa.Column("user_agent", sa.String(length=255), nullable=True))
    op.add_column("refresh_tokens", sa.Column("ip_address", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("refresh_tokens", "ip_address")
    op.drop_column("refresh_tokens", "user_agent")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
