"""Add customer master data fields.

Revision ID: 3c4d5e6f7a8b
Revises: 2f6a8c1b0d3e
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3c4d5e6f7a8b"
down_revision = "2f6a8c1b0d3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    customer_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="customer_status")
    customer_status.create(op.get_bind(), checkfirst=True)

    op.add_column("customers", sa.Column("code", sa.String(length=50), nullable=True))
    op.add_column("customers", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "customers",
        sa.Column("status", customer_status, nullable=False, server_default="ACTIVE"),
    )
    op.add_column("customers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("customers", sa.Column("metadata", postgresql.JSONB(), nullable=True))

    op.execute(
        "UPDATE customers "
        "SET code = CONCAT('CUST-', REPLACE(id::text, '-', '')) "
        "WHERE code IS NULL"
    )
    op.execute("UPDATE customers SET status = 'DELETED' WHERE COALESCE(is_deleted, FALSE) = TRUE")
    op.execute("UPDATE customers SET deleted_at = NOW() WHERE status = 'DELETED' AND deleted_at IS NULL")

    op.alter_column("customers", "code", nullable=False)
    op.alter_column("customers", "tenant_id", nullable=False)
    op.create_unique_constraint("uq_customers_tenant_code", "customers", ["tenant_id", "code"])


def downgrade() -> None:
    op.drop_constraint("uq_customers_tenant_code", "customers", type_="unique")
    op.alter_column("customers", "tenant_id", nullable=True)
    op.drop_column("customers", "metadata")
    op.drop_column("customers", "deleted_at")
    op.drop_column("customers", "status")
    op.drop_column("customers", "notes")
    op.drop_column("customers", "code")

    customer_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="customer_status")
    customer_status.drop(op.get_bind(), checkfirst=True)
