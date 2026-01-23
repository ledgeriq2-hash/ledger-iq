"""Add inventory foundation tables (Sprint 13).

Revision ID: 0009_sprint13_inventory
Revises: 0008_sprint12_purchase_invoices
Create Date: 2026-01-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_sprint13_inventory"
down_revision = "0008_sprint12_purchase_invoices"
branch_labels = None
depends_on = None

product_status_enum = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    name="product_status",
    create_type=False,
)

stock_move_direction_enum = postgresql.ENUM(
    "IN",
    "OUT",
    name="stock_move_direction",
    create_type=False,
)


def upgrade() -> None:
    product_status_enum.create(op.get_bind(), checkfirst=True)
    stock_move_direction_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "units",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_base", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_units_tenant_code"),
    )
    op.create_index("ix_units_tenant_id", "units", ["tenant_id"], unique=False)
    op.create_index("ix_units_created_at", "units", ["created_at"], unique=False)

    op.add_column(
        "products",
        sa.Column("status", product_status_enum, nullable=False, server_default=sa.text("'ACTIVE'")),
    )
    op.add_column("products", sa.Column("base_unit_id", sa.UUID(), nullable=True))
    op.add_column("products", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("metadata", postgresql.JSONB(), nullable=True))
    op.create_foreign_key(
        "fk_products_base_unit_id",
        "products",
        "units",
        ["base_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_products_tenant_sku", "products", ["tenant_id", "sku"])
    op.create_index("ix_products_tenant_status", "products", ["tenant_id", "status"], unique=False)

    op.create_table(
        "unit_conversions",
        sa.Column("from_unit_id", sa.UUID(), nullable=False),
        sa.Column("to_unit_id", sa.UUID(), nullable=False),
        sa.Column("multiplier", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["from_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "from_unit_id",
            "to_unit_id",
            name="uq_unit_conversions_tenant_from_to",
        ),
        sa.CheckConstraint("multiplier > 0", name="ck_unit_conversions_multiplier_positive"),
    )
    op.create_index("ix_unit_conversions_tenant_id", "unit_conversions", ["tenant_id"], unique=False)
    op.create_index("ix_unit_conversions_created_at", "unit_conversions", ["created_at"], unique=False)
    op.create_index("ix_unit_conversions_from_unit_id", "unit_conversions", ["from_unit_id"], unique=False)
    op.create_index("ix_unit_conversions_to_unit_id", "unit_conversions", ["to_unit_id"], unique=False)

    op.create_table(
        "stock_moves",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("move_date", sa.Date(), nullable=False),
        sa.Column("direction", stock_move_direction_enum, nullable=False),
        sa.Column("quantity_base", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("unit_id", sa.UUID(), nullable=True),
        sa.Column("quantity_original", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=False),
        sa.Column("reference_id", sa.UUID(), nullable=False),
        sa.Column("posted_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["posted_journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_moves_tenant_id", "stock_moves", ["tenant_id"], unique=False)
    op.create_index("ix_stock_moves_created_at", "stock_moves", ["created_at"], unique=False)
    op.create_index(
        "ix_stock_moves_tenant_product_date",
        "stock_moves",
        ["tenant_id", "product_id", "move_date"],
        unique=False,
    )
    op.create_index(
        "ix_stock_moves_tenant_reference",
        "stock_moves",
        ["tenant_id", "reference_type", "reference_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_moves_tenant_move_date",
        "stock_moves",
        ["tenant_id", "move_date"],
        unique=False,
    )

    op.create_table(
        "stock_balances",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("on_hand_qty_base", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "product_id", name="uq_stock_balances_tenant_product"),
    )
    op.create_index("ix_stock_balances_tenant_id", "stock_balances", ["tenant_id"], unique=False)
    op.create_index("ix_stock_balances_created_at", "stock_balances", ["created_at"], unique=False)
    op.create_index("ix_stock_balances_product_id", "stock_balances", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stock_balances_product_id", table_name="stock_balances")
    op.drop_index("ix_stock_balances_created_at", table_name="stock_balances")
    op.drop_index("ix_stock_balances_tenant_id", table_name="stock_balances")
    op.drop_table("stock_balances")

    op.drop_index("ix_stock_moves_tenant_move_date", table_name="stock_moves")
    op.drop_index("ix_stock_moves_tenant_reference", table_name="stock_moves")
    op.drop_index("ix_stock_moves_tenant_product_date", table_name="stock_moves")
    op.drop_index("ix_stock_moves_created_at", table_name="stock_moves")
    op.drop_index("ix_stock_moves_tenant_id", table_name="stock_moves")
    op.drop_table("stock_moves")

    op.drop_index("ix_unit_conversions_to_unit_id", table_name="unit_conversions")
    op.drop_index("ix_unit_conversions_from_unit_id", table_name="unit_conversions")
    op.drop_index("ix_unit_conversions_created_at", table_name="unit_conversions")
    op.drop_index("ix_unit_conversions_tenant_id", table_name="unit_conversions")
    op.drop_table("unit_conversions")

    op.drop_index("ix_products_tenant_status", table_name="products")
    op.drop_constraint("uq_products_tenant_sku", "products", type_="unique")
    op.drop_constraint("fk_products_base_unit_id", "products", type_="foreignkey")
    op.drop_column("products", "metadata")
    op.drop_column("products", "notes")
    op.drop_column("products", "base_unit_id")
    op.drop_column("products", "status")

    op.drop_index("ix_units_created_at", table_name="units")
    op.drop_index("ix_units_tenant_id", table_name="units")
    op.drop_table("units")

    stock_move_direction_enum.drop(op.get_bind(), checkfirst=True)
    product_status_enum.drop(op.get_bind(), checkfirst=True)
