"""Add missing tenant/created indexes for list tables.

Revision ID: 8c1a2e3f4d5b
Revises: d4c3b9c5c6f1
Create Date: 2025-12-13 12:45:00.000000
"""

from alembic import op
from sqlalchemy import inspect

revision = "8c1a2e3f4d5b"
down_revision = "d4c3b9c5c6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "gdpr_requests" in inspector.get_table_names():
        op.create_index(
            "ix_gdpr_requests_tenant_created",
            "gdpr_requests",
            ["tenant_id", "created_at"],
        )
    op.create_index(
        "ix_tenant_configs_tenant_created",
        "tenant_configs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_created",
        "tenant_subscriptions",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    op.drop_index("ix_tenant_subscriptions_tenant_created", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_configs_tenant_created", table_name="tenant_configs")
    if "gdpr_requests" in inspector.get_table_names():
        op.drop_index("ix_gdpr_requests_tenant_created", table_name="gdpr_requests")
