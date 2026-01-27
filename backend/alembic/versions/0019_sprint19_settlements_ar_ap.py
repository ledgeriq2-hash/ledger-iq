"""Sprint 19 settlements (customer receipts + vendor payments)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_sprint19_settlements_ar_ap"
down_revision = "0018_vendors_purchase_bills"
branch_labels = None
depends_on = None

customer_receipt_status_enum = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="customer_receipt_status",
    create_type=False,
)

vendor_payment_status_enum = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="vendor_payment_status",
    create_type=False,
)


def upgrade() -> None:
    customer_receipt_status_enum.create(op.get_bind(), checkfirst=True)
    vendor_payment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customer_receipts",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("receipt_no", sa.String(length=50), nullable=True),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column(
            "status",
            customer_receipt_status_enum,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column("amount_total", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("memo", sa.String(length=255), nullable=True),
        sa.Column("cash_account_id", sa.UUID(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posting_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["cash_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["posting_journal_entry_id"],
            ["journal_entries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_journal_entry_id"],
            ["journal_entries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "receipt_no", name="uq_customer_receipts_tenant_receipt_no"),
    )
    op.create_index("ix_customer_receipts_tenant_id", "customer_receipts", ["tenant_id"], unique=False)
    op.create_index("ix_customer_receipts_created_at", "customer_receipts", ["created_at"], unique=False)
    op.create_index("ix_customer_receipts_customer_id", "customer_receipts", ["customer_id"], unique=False)
    op.create_index("ix_customer_receipts_receipt_date", "customer_receipts", ["receipt_date"], unique=False)
    op.create_index("ix_customer_receipts_status", "customer_receipts", ["status"], unique=False)
    op.create_index(
        "ix_customer_receipts_tenant_customer", "customer_receipts", ["tenant_id", "customer_id"], unique=False
    )
    op.create_index("ix_customer_receipts_tenant_status", "customer_receipts", ["tenant_id", "status"], unique=False)

    op.create_table(
        "customer_receipt_allocations",
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("sales_invoice_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_customer_receipt_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["receipt_id"], ["customer_receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_invoice_id"], ["sales_invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "receipt_id",
            "sales_invoice_id",
            name="uq_customer_receipt_allocations_tenant_receipt_invoice",
        ),
    )
    op.create_index(
        "ix_customer_receipt_allocations_tenant_id", "customer_receipt_allocations", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_customer_receipt_allocations_created_at",
        "customer_receipt_allocations",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_receipt_allocations_receipt_id",
        "customer_receipt_allocations",
        ["receipt_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_receipt_allocations_sales_invoice_id",
        "customer_receipt_allocations",
        ["sales_invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_receipt_allocations_tenant_receipt",
        "customer_receipt_allocations",
        ["tenant_id", "receipt_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_receipt_allocations_tenant_invoice",
        "customer_receipt_allocations",
        ["tenant_id", "sales_invoice_id"],
        unique=False,
    )

    op.create_table(
        "vendor_payments",
        sa.Column("vendor_id", sa.UUID(), nullable=False),
        sa.Column("payment_no", sa.String(length=50), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column(
            "status",
            vendor_payment_status_enum,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column("amount_total", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("memo", sa.String(length=255), nullable=True),
        sa.Column("cash_account_id", sa.UUID(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posting_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["cash_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["posting_journal_entry_id"],
            ["journal_entries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_journal_entry_id"],
            ["journal_entries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "payment_no", name="uq_vendor_payments_tenant_payment_no"),
    )
    op.create_index("ix_vendor_payments_tenant_id", "vendor_payments", ["tenant_id"], unique=False)
    op.create_index("ix_vendor_payments_created_at", "vendor_payments", ["created_at"], unique=False)
    op.create_index("ix_vendor_payments_vendor_id", "vendor_payments", ["vendor_id"], unique=False)
    op.create_index("ix_vendor_payments_payment_date", "vendor_payments", ["payment_date"], unique=False)
    op.create_index("ix_vendor_payments_status", "vendor_payments", ["status"], unique=False)
    op.create_index("ix_vendor_payments_tenant_vendor", "vendor_payments", ["tenant_id", "vendor_id"], unique=False)
    op.create_index("ix_vendor_payments_tenant_status", "vendor_payments", ["tenant_id", "status"], unique=False)

    op.create_table(
        "vendor_payment_allocations",
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("purchase_bill_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_vendor_payment_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["payment_id"], ["vendor_payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_bill_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "payment_id",
            "purchase_bill_id",
            name="uq_vendor_payment_allocations_tenant_payment_bill",
        ),
    )
    op.create_index(
        "ix_vendor_payment_allocations_tenant_id", "vendor_payment_allocations", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_vendor_payment_allocations_created_at",
        "vendor_payment_allocations",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_payment_allocations_payment_id",
        "vendor_payment_allocations",
        ["payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_payment_allocations_purchase_bill_id",
        "vendor_payment_allocations",
        ["purchase_bill_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_payment_allocations_tenant_payment",
        "vendor_payment_allocations",
        ["tenant_id", "payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_payment_allocations_tenant_bill",
        "vendor_payment_allocations",
        ["tenant_id", "purchase_bill_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_vendor_payment_allocations_tenant_bill", table_name="vendor_payment_allocations")
    op.drop_index("ix_vendor_payment_allocations_tenant_payment", table_name="vendor_payment_allocations")
    op.drop_index("ix_vendor_payment_allocations_purchase_bill_id", table_name="vendor_payment_allocations")
    op.drop_index("ix_vendor_payment_allocations_payment_id", table_name="vendor_payment_allocations")
    op.drop_index("ix_vendor_payment_allocations_created_at", table_name="vendor_payment_allocations")
    op.drop_index("ix_vendor_payment_allocations_tenant_id", table_name="vendor_payment_allocations")
    op.drop_table("vendor_payment_allocations")

    op.drop_index("ix_vendor_payments_tenant_status", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_tenant_vendor", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_status", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_payment_date", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_vendor_id", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_created_at", table_name="vendor_payments")
    op.drop_index("ix_vendor_payments_tenant_id", table_name="vendor_payments")
    op.drop_table("vendor_payments")

    op.drop_index("ix_customer_receipt_allocations_tenant_invoice", table_name="customer_receipt_allocations")
    op.drop_index("ix_customer_receipt_allocations_tenant_receipt", table_name="customer_receipt_allocations")
    op.drop_index("ix_customer_receipt_allocations_sales_invoice_id", table_name="customer_receipt_allocations")
    op.drop_index("ix_customer_receipt_allocations_receipt_id", table_name="customer_receipt_allocations")
    op.drop_index("ix_customer_receipt_allocations_created_at", table_name="customer_receipt_allocations")
    op.drop_index("ix_customer_receipt_allocations_tenant_id", table_name="customer_receipt_allocations")
    op.drop_table("customer_receipt_allocations")

    op.drop_index("ix_customer_receipts_tenant_status", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_tenant_customer", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_status", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_receipt_date", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_customer_id", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_created_at", table_name="customer_receipts")
    op.drop_index("ix_customer_receipts_tenant_id", table_name="customer_receipts")
    op.drop_table("customer_receipts")

    vendor_payment_status_enum.drop(op.get_bind(), checkfirst=True)
    customer_receipt_status_enum.drop(op.get_bind(), checkfirst=True)
