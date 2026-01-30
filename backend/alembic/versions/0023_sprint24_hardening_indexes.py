"""Hardening indexes (Sprint 24).

Revision ID: 0023_sprint24_hardening_indexes
Revises: 0022_sprint22_portal_links
Create Date: 2026-01-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_sprint24_hardening_indexes"
down_revision = "0022_sprint22_portal_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_invoices_tenant_customer_status_created",
        "invoices",
        ["tenant_id", "customer_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payments_tenant_customer_created",
        "payments",
        ["tenant_id", "customer_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_portal_tokens_tenant_entity_expires",
        "portal_tokens",
        ["tenant_id", "entity_type", "entity_id", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_tokens_tenant_entity_expires", table_name="portal_tokens")
    op.drop_index("ix_payments_tenant_customer_created", table_name="payments")
    op.drop_index("ix_invoices_tenant_customer_status_created", table_name="invoices")
