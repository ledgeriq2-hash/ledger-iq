"""Add unique constraint for reports cache entries.

Revision ID: c9f8a1b2c3d4
Revises: adb123456789, b2c3d4e5f6
Create Date: 2025-12-27 00:00:00.000000
"""

from alembic import op

revision = "c9f8a1b2c3d4"
down_revision = ("adb123456789", "b2c3d4e5f6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY tenant_id, report_type, params_hash
                    ORDER BY created_at DESC, id DESC
                ) AS rn
            FROM reports_cache
        )
        DELETE FROM reports_cache
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )
    op.create_unique_constraint(
        "uq_reports_cache_tenant_report_params",
        "reports_cache",
        ["tenant_id", "report_type", "params_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_reports_cache_tenant_report_params",
        "reports_cache",
        type_="unique",
    )
