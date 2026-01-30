"""Add portal token revoke support (Sprint 22).

Revision ID: 0022_sprint22_portal_links
Revises: 0021_inventory_stock_ledger
Create Date: 2026-01-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_sprint22_portal_links"
down_revision = "0021_inventory_stock_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portal_tokens", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_portal_tokens_tenant_entity_created",
        "portal_tokens",
        ["tenant_id", "entity_type", "entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_tokens_tenant_entity_created", table_name="portal_tokens")
    op.drop_column("portal_tokens", "revoked_at")
