"""Enforce tenant constraint on portal tokens.

Revision ID: b2c3d4e5f6
Revises: a1b2c3d4e5f6
Create Date: 2025-12-25 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure there are no NULL tenant_ids before toggling the constraint.
    op.execute("DELETE FROM portal_tokens WHERE tenant_id IS NULL")

    op.alter_column(
        "portal_tokens",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_portal_tokens_tenant_id_tenants",
        "portal_tokens",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_portal_tokens_tenant_entity_token",
        "portal_tokens",
        ["tenant_id", "entity_type", "entity_id", "token_hash"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_portal_tokens_tenant_entity_token", "portal_tokens", type_="unique")
    op.drop_constraint("fk_portal_tokens_tenant_id_tenants", "portal_tokens", type_="foreignkey")
    op.alter_column(
        "portal_tokens",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
