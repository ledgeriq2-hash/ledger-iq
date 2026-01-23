"""Link invoice lines to products/units for inventory (Sprint 14).

Revision ID: 0010_sprint14_inventory_link
Revises: 0009_sprint13_inventory
Create Date: 2026-01-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_sprint14_inventory_link"
down_revision = "0009_sprint13_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_invoice_lines", sa.Column("product_id", sa.UUID(), nullable=True))
    op.add_column("sales_invoice_lines", sa.Column("unit_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_sales_invoice_lines_product_id",
        "sales_invoice_lines",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sales_invoice_lines_unit_id",
        "sales_invoice_lines",
        "units",
        ["unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sales_invoice_lines_product_id",
        "sales_invoice_lines",
        ["product_id"],
        unique=False,
    )

    op.add_column("purchase_invoice_lines", sa.Column("product_id", sa.UUID(), nullable=True))
    op.add_column("purchase_invoice_lines", sa.Column("unit_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_purchase_invoice_lines_product_id",
        "purchase_invoice_lines",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_purchase_invoice_lines_unit_id",
        "purchase_invoice_lines",
        "units",
        ["unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_purchase_invoice_lines_product_id",
        "purchase_invoice_lines",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_purchase_invoice_lines_product_id", table_name="purchase_invoice_lines")
    op.drop_constraint(
        "fk_purchase_invoice_lines_unit_id",
        "purchase_invoice_lines",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_purchase_invoice_lines_product_id",
        "purchase_invoice_lines",
        type_="foreignkey",
    )
    op.drop_column("purchase_invoice_lines", "unit_id")
    op.drop_column("purchase_invoice_lines", "product_id")

    op.drop_index("ix_sales_invoice_lines_product_id", table_name="sales_invoice_lines")
    op.drop_constraint(
        "fk_sales_invoice_lines_unit_id",
        "sales_invoice_lines",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_sales_invoice_lines_product_id",
        "sales_invoice_lines",
        type_="foreignkey",
    )
    op.drop_column("sales_invoice_lines", "unit_id")
    op.drop_column("sales_invoice_lines", "product_id")
