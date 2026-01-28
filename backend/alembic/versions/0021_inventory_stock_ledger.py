"""Inventory stock ledger core (Sprint 21).

Revision ID: 0021_inventory_stock_ledger
Revises: 0020_sprint20_fx_tax
Create Date: 2026-01-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021_inventory_stock_ledger"
down_revision = "0020_sprint20_fx_tax"
branch_labels = None
depends_on = None

stock_move_source_enum = postgresql.ENUM(
    "PURCHASE",
    "SALE",
    "REVERSAL",
    name="stock_move_source_type",
    create_type=False,
)


def upgrade() -> None:
    op.rename_table("units", "inventory_units")
    op.add_column(
        "inventory_units",
        sa.Column(
            "ratio_to_base",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    op.add_column("products", sa.Column("code", sa.String(length=20), nullable=True))
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )
    op.create_index("ix_products_tenant_code", "products", ["tenant_id", "code"], unique=False)

    op.execute(
        """
        UPDATE products
        SET is_active = CASE WHEN status = 'INACTIVE' THEN FALSE ELSE TRUE END
        WHERE is_active IS NULL
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   tenant_id,
                   row_number() OVER (PARTITION BY tenant_id ORDER BY created_at, id) AS rn
            FROM products
            WHERE code IS NULL
        )
        UPDATE products
        SET code = 'PROD-' || lpad(ranked.rn::text, 6, '0')
        FROM ranked
        WHERE products.id = ranked.id
        """
    )
    op.alter_column("products", "code", nullable=False)
    op.create_unique_constraint("uq_products_tenant_code", "products", ["tenant_id", "code"])

    stock_move_source_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "stock_moves",
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "stock_moves",
        sa.Column(
            "base_quantity",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column("stock_moves", sa.Column("source_type", stock_move_source_enum, nullable=True))
    op.add_column("stock_moves", sa.Column("source_id", sa.UUID(), nullable=True))
    op.add_column(
        "stock_moves",
        sa.Column(
            "posted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column("stock_moves", sa.Column("reversed_stock_move_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_stock_moves_reversed_stock_move_id",
        "stock_moves",
        "stock_moves",
        ["reversed_stock_move_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_stock_moves_tenant_source",
        "stock_moves",
        ["tenant_id", "source_type", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_moves_tenant_product_posted",
        "stock_moves",
        ["tenant_id", "product_id", "posted_at"],
        unique=False,
    )

    op.execute(
        """
        UPDATE stock_moves
        SET source_id = reference_id,
            posted_at = move_date::timestamp at time zone 'UTC',
            base_quantity = CASE WHEN direction = 'OUT' THEN -quantity_base ELSE quantity_base END,
            quantity = CASE
                WHEN quantity_original IS NOT NULL THEN
                    CASE WHEN direction = 'OUT' THEN -quantity_original ELSE quantity_original END
                ELSE
                    CASE WHEN direction = 'OUT' THEN -quantity_base ELSE quantity_base END
            END,
            source_type = (CASE
                WHEN lower(reference_type) LIKE '%purchase%' THEN 'PURCHASE'
                WHEN lower(reference_type) LIKE '%sale%' THEN 'SALE'
                WHEN lower(reference_type) LIKE '%reverse%' THEN 'REVERSAL'
                ELSE CASE WHEN direction = 'OUT' THEN 'SALE' ELSE 'PURCHASE' END
            END)::stock_move_source_type
        WHERE source_id IS NULL OR source_type IS NULL
        """
    )
    op.alter_column("stock_moves", "source_type", nullable=False)
    op.alter_column("stock_moves", "source_id", nullable=False)
    op.alter_column("stock_moves", "posted_at", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_stock_moves_tenant_product_posted", table_name="stock_moves")
    op.drop_index("ix_stock_moves_tenant_source", table_name="stock_moves")
    op.drop_constraint(
        "fk_stock_moves_reversed_stock_move_id",
        "stock_moves",
        type_="foreignkey",
    )
    op.drop_column("stock_moves", "reversed_stock_move_id")
    op.drop_column("stock_moves", "posted_at")
    op.drop_column("stock_moves", "source_id")
    op.drop_column("stock_moves", "source_type")
    op.drop_column("stock_moves", "base_quantity")
    op.drop_column("stock_moves", "quantity")
    stock_move_source_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("uq_products_tenant_code", "products", type_="unique")
    op.drop_index("ix_products_tenant_code", table_name="products")
    op.drop_column("products", "is_active")
    op.drop_column("products", "code")

    op.drop_column("inventory_units", "ratio_to_base")
    op.rename_table("inventory_units", "units")
