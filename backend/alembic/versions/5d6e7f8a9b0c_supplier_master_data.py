"""Add supplier master data fields.

Revision ID: 5d6e7f8a9b0c
Revises: 3c4d5e6f7a8b
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "5d6e7f8a9b0c"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    supplier_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="supplier_status")
    supplier_status.create(op.get_bind(), checkfirst=True)

    op.add_column("suppliers", sa.Column("code", sa.String(length=50), nullable=True))
    op.add_column(
        "suppliers",
        sa.Column("status", supplier_status, nullable=False, server_default="ACTIVE"),
    )
    op.add_column("suppliers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("suppliers", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE suppliers "
        "SET code = CONCAT('SUP-', REPLACE(id::text, '-', '')) "
        "WHERE code IS NULL"
    )
    op.execute("UPDATE suppliers SET status = 'DELETED' WHERE COALESCE(is_deleted, FALSE) = TRUE")
    op.execute("UPDATE suppliers SET deleted_at = NOW() WHERE status = 'DELETED' AND deleted_at IS NULL")

    op.alter_column("suppliers", "code", nullable=False)
    op.alter_column("suppliers", "tenant_id", nullable=False)
    op.create_unique_constraint("uq_suppliers_tenant_code", "suppliers", ["tenant_id", "code"])
    op.create_index("ix_suppliers_tenant_status", "suppliers", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_suppliers_tenant_status", table_name="suppliers")
    op.drop_constraint("uq_suppliers_tenant_code", "suppliers", type_="unique")
    op.alter_column("suppliers", "tenant_id", nullable=True)
    op.drop_column("suppliers", "deactivated_at")
    op.drop_column("suppliers", "deleted_at")
    op.drop_column("suppliers", "status")
    op.drop_column("suppliers", "code")

    supplier_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="supplier_status")
    supplier_status.drop(op.get_bind(), checkfirst=True)
