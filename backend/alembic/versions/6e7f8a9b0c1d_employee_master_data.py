"""Add employee master data fields.

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "6e7f8a9b0c1d"
down_revision = "5d6e7f8a9b0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    employee_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="employee_status")
    employee_status.create(op.get_bind(), checkfirst=True)

    op.add_column("employees", sa.Column("code", sa.String(length=50), nullable=True))
    op.add_column(
        "employees",
        sa.Column("status", employee_status, nullable=False, server_default="ACTIVE"),
    )
    op.add_column("employees", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("employees", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE employees "
        "SET code = CONCAT('EMP-', REPLACE(id::text, '-', '')) "
        "WHERE code IS NULL"
    )
    op.execute("UPDATE employees SET status = 'DELETED' WHERE COALESCE(is_deleted, FALSE) = TRUE")
    op.execute("UPDATE employees SET deleted_at = NOW() WHERE status = 'DELETED' AND deleted_at IS NULL")

    op.alter_column("employees", "code", nullable=False)
    op.alter_column("employees", "tenant_id", nullable=False)
    op.create_unique_constraint("uq_employees_tenant_code", "employees", ["tenant_id", "code"])
    op.create_index("ix_employees_tenant_status", "employees", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_employees_tenant_status", table_name="employees")
    op.drop_constraint("uq_employees_tenant_code", "employees", type_="unique")
    op.alter_column("employees", "tenant_id", nullable=True)
    op.drop_column("employees", "deactivated_at")
    op.drop_column("employees", "deleted_at")
    op.drop_column("employees", "status")
    op.drop_column("employees", "code")

    employee_status = sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="employee_status")
    employee_status.drop(op.get_bind(), checkfirst=True)
