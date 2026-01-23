"""Add treasury cash accounts and transactions (Sprint 9).

Revision ID: 0006_sprint9_treasury_cash
Revises: 0005_sprint8_dimensions
Create Date: 2026-01-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_sprint9_treasury_cash"
down_revision = "0005_sprint8_dimensions"
branch_labels = None
depends_on = None

cash_transaction_type_enum = sa.Enum(
    "RECEIPT",
    "PAYMENT",
    "TRANSFER",
    name="treasury_cash_transaction_type",
)

cash_transaction_status_enum = sa.Enum(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="treasury_cash_transaction_status",
)


def upgrade() -> None:
    op.create_table(
        "treasury_cash_accounts",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_cash_accounts_tenant_id", "treasury_cash_accounts", ["tenant_id"], unique=False)
    op.create_index("ix_treasury_cash_accounts_created_at", "treasury_cash_accounts", ["created_at"], unique=False)
    op.create_index("ix_treasury_cash_accounts_account_id", "treasury_cash_accounts", ["account_id"], unique=False)
    op.create_index("ix_treasury_cash_accounts_name", "treasury_cash_accounts", ["name"], unique=False)

    op.create_table(
        "treasury_cash_transactions",
        sa.Column("transaction_type", cash_transaction_type_enum, nullable=False),
        sa.Column("status", cash_transaction_status_enum, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("posting_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("cash_account_id", sa.UUID(), nullable=True),
        sa.Column("counterparty_account_id", sa.UUID(), nullable=True),
        sa.Column("from_cash_account_id", sa.UUID(), nullable=True),
        sa.Column("to_cash_account_id", sa.UUID(), nullable=True),
        sa.Column("journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("reversal_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_reason", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["cash_account_id"], ["treasury_cash_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["counterparty_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_cash_account_id"], ["treasury_cash_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_cash_account_id"], ["treasury_cash_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversal_journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_treasury_cash_transactions_amount_positive"),
        sa.CheckConstraint(
            "(transaction_type IN ('RECEIPT', 'PAYMENT') AND cash_account_id IS NOT NULL "
            "AND counterparty_account_id IS NOT NULL AND from_cash_account_id IS NULL "
            "AND to_cash_account_id IS NULL) "
            "OR (transaction_type = 'TRANSFER' AND from_cash_account_id IS NOT NULL "
            "AND to_cash_account_id IS NOT NULL AND from_cash_account_id <> to_cash_account_id "
            "AND cash_account_id IS NULL AND counterparty_account_id IS NULL)",
            name="ck_treasury_cash_transactions_type_accounts",
        ),
    )
    op.create_index("ix_treasury_cash_transactions_tenant_id", "treasury_cash_transactions", ["tenant_id"], unique=False)
    op.create_index("ix_treasury_cash_transactions_created_at", "treasury_cash_transactions", ["created_at"], unique=False)
    op.create_index("ix_treasury_cash_transactions_posting_date", "treasury_cash_transactions", ["posting_date"], unique=False)
    op.create_index("ix_treasury_cash_transactions_status", "treasury_cash_transactions", ["status"], unique=False)
    op.create_index(
        "ix_treasury_cash_transactions_transaction_type",
        "treasury_cash_transactions",
        ["transaction_type"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_cash_account_id",
        "treasury_cash_transactions",
        ["cash_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_from_cash_account_id",
        "treasury_cash_transactions",
        ["from_cash_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_to_cash_account_id",
        "treasury_cash_transactions",
        ["to_cash_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_counterparty_account_id",
        "treasury_cash_transactions",
        ["counterparty_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_journal_entry_id",
        "treasury_cash_transactions",
        ["journal_entry_id"],
        unique=False,
    )
    op.create_index(
        "ix_treasury_cash_transactions_reversal_journal_entry_id",
        "treasury_cash_transactions",
        ["reversal_journal_entry_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_treasury_cash_transactions_reversal_journal_entry_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_journal_entry_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_counterparty_account_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_to_cash_account_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_from_cash_account_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_cash_account_id", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_transaction_type", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_status", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_posting_date", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_created_at", table_name="treasury_cash_transactions")
    op.drop_index("ix_treasury_cash_transactions_tenant_id", table_name="treasury_cash_transactions")
    op.drop_table("treasury_cash_transactions")

    op.drop_index("ix_treasury_cash_accounts_name", table_name="treasury_cash_accounts")
    op.drop_index("ix_treasury_cash_accounts_account_id", table_name="treasury_cash_accounts")
    op.drop_index("ix_treasury_cash_accounts_created_at", table_name="treasury_cash_accounts")
    op.drop_index("ix_treasury_cash_accounts_tenant_id", table_name="treasury_cash_accounts")
    op.drop_table("treasury_cash_accounts")

    bind = op.get_bind()
    cash_transaction_status_enum.drop(bind, checkfirst=True)
    cash_transaction_type_enum.drop(bind, checkfirst=True)
