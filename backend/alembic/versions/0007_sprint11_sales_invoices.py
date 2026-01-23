"""Add sales invoices and customer fields (Sprint 11).

Revision ID: 0007_sprint11_sales_invoices
Revises: 0006_sprint9_treasury_cash
Create Date: 2026-01-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_sprint11_sales_invoices"
down_revision = "0006_sprint9_treasury_cash"
branch_labels = None
depends_on = None

sales_invoice_status_enum = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="sales_invoice_status",
    create_type=False,
)


def upgrade() -> None:
    sales_invoice_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("customers", sa.Column("currency_code", sa.String(length=10), nullable=True))
    op.add_column("customers", sa.Column("payment_terms_days", sa.Integer(), nullable=True))

    op.create_table(
        "sales_invoices",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("invoice_no", sa.String(length=50), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("status", sales_invoice_status_enum, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "invoice_no", name="uq_sales_invoices_tenant_invoice_no"),
    )
    op.create_index("ix_sales_invoices_tenant_id", "sales_invoices", ["tenant_id"], unique=False)
    op.create_index("ix_sales_invoices_created_at", "sales_invoices", ["created_at"], unique=False)
    op.create_index("ix_sales_invoices_customer_id", "sales_invoices", ["customer_id"], unique=False)
    op.create_index("ix_sales_invoices_invoice_date", "sales_invoices", ["invoice_date"], unique=False)
    op.create_index("ix_sales_invoices_status", "sales_invoices", ["status"], unique=False)

    op.create_table(
        "sales_invoice_lines",
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("revenue_account_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["sales_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revenue_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_invoice_lines_tenant_id", "sales_invoice_lines", ["tenant_id"], unique=False)
    op.create_index("ix_sales_invoice_lines_created_at", "sales_invoice_lines", ["created_at"], unique=False)
    op.create_index("ix_sales_invoice_lines_invoice_id", "sales_invoice_lines", ["invoice_id"], unique=False)
    op.create_index(
        "ix_sales_invoice_lines_revenue_account_id",
        "sales_invoice_lines",
        ["revenue_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sales_invoice_lines_revenue_account_id", table_name="sales_invoice_lines")
    op.drop_index("ix_sales_invoice_lines_invoice_id", table_name="sales_invoice_lines")
    op.drop_index("ix_sales_invoice_lines_created_at", table_name="sales_invoice_lines")
    op.drop_index("ix_sales_invoice_lines_tenant_id", table_name="sales_invoice_lines")
    op.drop_table("sales_invoice_lines")

    op.drop_index("ix_sales_invoices_status", table_name="sales_invoices")
    op.drop_index("ix_sales_invoices_invoice_date", table_name="sales_invoices")
    op.drop_index("ix_sales_invoices_customer_id", table_name="sales_invoices")
    op.drop_index("ix_sales_invoices_created_at", table_name="sales_invoices")
    op.drop_index("ix_sales_invoices_tenant_id", table_name="sales_invoices")
    op.drop_table("sales_invoices")

    op.drop_column("customers", "payment_terms_days")
    op.drop_column("customers", "currency_code")

    sales_invoice_status_enum.drop(op.get_bind(), checkfirst=True)
