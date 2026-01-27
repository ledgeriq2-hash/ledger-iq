"""Sprint 18 vendors + purchase bills core fields."""

from alembic import op
import sqlalchemy as sa


revision = "0018_vendors_purchase_bills"
down_revision = "0017_customers_sales_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vendors") as batch:
        batch.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("phone", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("address_line1", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("address_line2", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("city", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("country", sa.String(length=100), nullable=True))

    with op.batch_alter_table("purchase_invoices") as batch:
        batch.alter_column("invoice_no", existing_type=sa.String(length=50), nullable=True)
        batch.add_column(sa.Column("due_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("memo", sa.Text(), nullable=True))
        batch.add_column(sa.Column("subtotal", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("posting_journal_entry_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("reversal_journal_entry_id", sa.UUID(), nullable=True))
        batch.create_index("ix_purchase_invoices_tenant_vendor", ["tenant_id", "vendor_id"])
        batch.create_index("ix_purchase_invoices_tenant_status", ["tenant_id", "status"])
        batch.create_foreign_key(
            "fk_purchase_invoices_posting_journal_entry_id",
            "journal_entries",
            ["posting_journal_entry_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_purchase_invoices_reversal_journal_entry_id",
            "journal_entries",
            ["reversal_journal_entry_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute("UPDATE purchase_invoices SET subtotal = total_amount WHERE subtotal = 0")
    op.execute("UPDATE purchase_invoices SET total = total_amount WHERE total = 0")

    with op.batch_alter_table("purchase_invoice_lines") as batch:
        batch.drop_constraint("uq_purchase_invoice_lines_invoice_line", type_="unique")
        batch.create_index("ix_purchase_invoice_lines_tenant_invoice", ["tenant_id", "invoice_id"])
        batch.create_unique_constraint(
            "uq_purchase_invoice_lines_tenant_invoice_line_no",
            ["tenant_id", "invoice_id", "line_no"],
        )


def downgrade() -> None:
    with op.batch_alter_table("purchase_invoice_lines") as batch:
        batch.drop_constraint("uq_purchase_invoice_lines_tenant_invoice_line_no", type_="unique")
        batch.drop_index("ix_purchase_invoice_lines_tenant_invoice")
        batch.create_unique_constraint(
            "uq_purchase_invoice_lines_invoice_line",
            ["invoice_id", "line_no"],
        )

    with op.batch_alter_table("purchase_invoices") as batch:
        batch.drop_constraint("fk_purchase_invoices_reversal_journal_entry_id", type_="foreignkey")
        batch.drop_constraint("fk_purchase_invoices_posting_journal_entry_id", type_="foreignkey")
        batch.drop_index("ix_purchase_invoices_tenant_status")
        batch.drop_index("ix_purchase_invoices_tenant_vendor")
        batch.drop_column("reversal_journal_entry_id")
        batch.drop_column("posting_journal_entry_id")
        batch.drop_column("total")
        batch.drop_column("subtotal")
        batch.drop_column("memo")
        batch.drop_column("due_date")
        batch.alter_column("invoice_no", existing_type=sa.String(length=50), nullable=False)

    with op.batch_alter_table("vendors") as batch:
        batch.drop_column("country")
        batch.drop_column("city")
        batch.drop_column("address_line2")
        batch.drop_column("address_line1")
        batch.drop_column("phone")
        batch.drop_column("email")
