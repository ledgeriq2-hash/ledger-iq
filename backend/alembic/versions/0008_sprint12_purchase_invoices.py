"""Add vendors and purchase invoices (Sprint 12).

Revision ID: 0008_sprint12_purchase_invoices
Revises: 0007_sprint11_sales_invoices
Create Date: 2026-01-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_sprint12_purchase_invoices"
down_revision = "0007_sprint11_sales_invoices"
branch_labels = None
depends_on = None

vendor_status_enum = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    name="vendor_status",
    create_type=False,
)

purchase_invoice_status_enum = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="purchase_invoice_status",
    create_type=False,
)


def upgrade() -> None:
    vendor_status_enum.create(op.get_bind(), checkfirst=True)
    purchase_invoice_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "vendors",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", vendor_status_enum, nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_vendors_tenant_code"),
    )
    op.create_index("ix_vendors_tenant_id", "vendors", ["tenant_id"], unique=False)
    op.create_index("ix_vendors_created_at", "vendors", ["created_at"], unique=False)
    op.create_index("ix_vendors_tenant_status", "vendors", ["tenant_id", "status"], unique=False)
    op.create_index("ix_vendors_tenant_name", "vendors", ["tenant_id", "name"], unique=False)

    op.create_table(
        "purchase_invoices",
        sa.Column("vendor_id", sa.UUID(), nullable=False),
        sa.Column("invoice_no", sa.String(length=50), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("status", purchase_invoice_status_enum, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "invoice_no", name="uq_purchase_invoices_tenant_invoice_no"),
    )
    op.create_index("ix_purchase_invoices_tenant_id", "purchase_invoices", ["tenant_id"], unique=False)
    op.create_index("ix_purchase_invoices_created_at", "purchase_invoices", ["created_at"], unique=False)
    op.create_index("ix_purchase_invoices_vendor_id", "purchase_invoices", ["vendor_id"], unique=False)
    op.create_index("ix_purchase_invoices_invoice_date", "purchase_invoices", ["invoice_date"], unique=False)
    op.create_index("ix_purchase_invoices_status", "purchase_invoices", ["status"], unique=False)

    op.create_table(
        "purchase_invoice_lines",
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("expense_account_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expense_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "line_no", name="uq_purchase_invoice_lines_invoice_line"),
    )
    op.create_index("ix_purchase_invoice_lines_tenant_id", "purchase_invoice_lines", ["tenant_id"], unique=False)
    op.create_index("ix_purchase_invoice_lines_created_at", "purchase_invoice_lines", ["created_at"], unique=False)
    op.create_index("ix_purchase_invoice_lines_invoice_id", "purchase_invoice_lines", ["invoice_id"], unique=False)
    op.create_index(
        "ix_purchase_invoice_lines_expense_account_id",
        "purchase_invoice_lines",
        ["expense_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_purchase_invoice_lines_expense_account_id", table_name="purchase_invoice_lines")
    op.drop_index("ix_purchase_invoice_lines_invoice_id", table_name="purchase_invoice_lines")
    op.drop_index("ix_purchase_invoice_lines_created_at", table_name="purchase_invoice_lines")
    op.drop_index("ix_purchase_invoice_lines_tenant_id", table_name="purchase_invoice_lines")
    op.drop_table("purchase_invoice_lines")

    op.drop_index("ix_purchase_invoices_status", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_invoice_date", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_vendor_id", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_created_at", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_tenant_id", table_name="purchase_invoices")
    op.drop_table("purchase_invoices")

    op.drop_index("ix_vendors_tenant_name", table_name="vendors")
    op.drop_index("ix_vendors_tenant_status", table_name="vendors")
    op.drop_index("ix_vendors_created_at", table_name="vendors")
    op.drop_index("ix_vendors_tenant_id", table_name="vendors")
    op.drop_table("vendors")

    purchase_invoice_status_enum.drop(op.get_bind(), checkfirst=True)
    vendor_status_enum.drop(op.get_bind(), checkfirst=True)
