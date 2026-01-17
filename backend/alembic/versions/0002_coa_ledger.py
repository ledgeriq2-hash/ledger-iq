"""COA and ledger core tables.

Revision ID: 0002_coa_ledger
Revises: 4243ee2867e3
Create Date: 2026-01-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0002_coa_ledger"
down_revision = "4243ee2867e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accounts"):
        op.create_table(
            "accounts",
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("type", sa.String(length=32), nullable=False),
            sa.Column("normal_balance", sa.String(length=16), nullable=False),
            sa.Column("parent_id", sa.UUID(), nullable=True),
            sa.Column("is_system", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
            sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["accounts.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
        op.create_index("ix_accounts_created_at", "accounts", ["created_at"])
        op.create_unique_constraint("uq_accounts_tenant_code", "accounts", ["tenant_id", "code"])

    if not inspector.has_table("account_mappings"):
        op.create_table(
            "account_mappings",
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("account_id", sa.UUID(), nullable=False),
            sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_account_mappings_tenant_id", "account_mappings", ["tenant_id"])
        op.create_index("ix_account_mappings_created_at", "account_mappings", ["created_at"])
        op.create_unique_constraint("uq_account_mappings_tenant_key", "account_mappings", ["tenant_id", "key"])

    if not inspector.has_table("journal_lines"):
        op.create_table(
            "journal_lines",
            sa.Column("entry_id", sa.UUID(), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.UUID(), nullable=False),
            sa.Column("debit_amount", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False),
            sa.Column("credit_amount", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False),
            sa.Column("line_currency", sa.String(length=10), nullable=False),
            sa.Column("fx_rate", sa.Numeric(precision=18, scale=8), nullable=True),
            sa.Column("debit_base", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False),
            sa.Column("credit_base", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False),
            sa.Column("memo", sa.Text(), nullable=True),
            sa.Column("dimensions", JSONB(), nullable=True),
            sa.Column("tax_code", sa.String(length=50), nullable=True),
            sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["entry_id"], ["journal_entries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("entry_id", "line_no", name="uq_journal_lines_entry_line"),
        )
        op.create_index("ix_journal_lines_tenant_id", "journal_lines", ["tenant_id"])
        op.create_index("ix_journal_lines_created_at", "journal_lines", ["created_at"])
        op.create_index("ix_journal_lines_entry_id", "journal_lines", ["entry_id"])
        op.create_index("ix_journal_lines_account_id", "journal_lines", ["account_id"])

    if inspector.has_table("journal_entries"):
        columns = {column["name"] for column in inspector.get_columns("journal_entries")}

        with op.batch_alter_table("journal_entries") as batch:
            if "entry_no" not in columns:
                batch.add_column(
                    sa.Column("entry_no", sa.String(length=50), server_default=sa.text("uuid_generate_v4()"), nullable=False)
                )
            if "entry_date" not in columns:
                batch.add_column(
                    sa.Column("entry_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False)
                )
            if "posting_date" not in columns:
                batch.add_column(sa.Column("posting_date", sa.DateTime(timezone=True), nullable=True))
            if "period_year" not in columns:
                batch.add_column(
                    sa.Column(
                        "period_year",
                        sa.Integer(),
                        server_default=sa.text("EXTRACT(YEAR FROM CURRENT_DATE)::int"),
                        nullable=False,
                    )
                )
            if "period_month" not in columns:
                batch.add_column(
                    sa.Column(
                        "period_month",
                        sa.Integer(),
                        server_default=sa.text("EXTRACT(MONTH FROM CURRENT_DATE)::int"),
                        nullable=False,
                    )
                )
            if "status" not in columns:
                batch.add_column(
                    sa.Column("status", sa.String(length=16), server_default=sa.text("'Posted'"), nullable=False)
                )
            if "source_type" not in columns:
                batch.add_column(
                    sa.Column("source_type", sa.String(length=50), server_default=sa.text("'legacy'"), nullable=False)
                )
            if "memo" not in columns:
                batch.add_column(sa.Column("memo", sa.Text(), nullable=True))
            if "base_currency" not in columns:
                batch.add_column(
                    sa.Column("base_currency", sa.String(length=10), server_default=sa.text("'USD'"), nullable=False)
                )
            if "total_debit_base" not in columns:
                batch.add_column(
                    sa.Column("total_debit_base", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False)
                )
            if "total_credit_base" not in columns:
                batch.add_column(
                    sa.Column("total_credit_base", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False)
                )
            if "reversal_of_entry_id" not in columns:
                batch.add_column(sa.Column("reversal_of_entry_id", sa.UUID(), nullable=True))
                batch.create_foreign_key(
                    "fk_journal_entries_reversal_of",
                    "journal_entries",
                    ["reversal_of_entry_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "created_by" not in columns:
                batch.add_column(sa.Column("created_by", sa.UUID(), nullable=True))
                batch.create_foreign_key(
                    "fk_journal_entries_created_by",
                    "users",
                    ["created_by"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "approved_by" not in columns:
                batch.add_column(sa.Column("approved_by", sa.UUID(), nullable=True))
                batch.create_foreign_key(
                    "fk_journal_entries_approved_by",
                    "users",
                    ["approved_by"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "posted_at" not in columns:
                batch.add_column(sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))

        indexes = {idx["name"] for idx in inspector.get_indexes("journal_entries")}
        if "ix_journal_entries_entry_date" not in indexes:
            op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])
        if "ix_journal_entries_period_year_month" not in indexes:
            op.create_index(
                "ix_journal_entries_period_year_month",
                "journal_entries",
                ["period_year", "period_month"],
            )
        if "ix_journal_entries_source_type_id" not in indexes:
            op.create_index(
                "ix_journal_entries_source_type_id",
                "journal_entries",
                ["source_type", "source_id"],
            )
        if "ix_journal_entries_entry_no" not in indexes:
            op.create_index(
                "ix_journal_entries_entry_no",
                "journal_entries",
                ["entry_no"],
                unique=True,
            )

        op.execute(
            "UPDATE journal_entries SET entry_date = COALESCE(entry_date, date, event_date, CURRENT_DATE)"
        )
        op.execute(
            "UPDATE journal_entries SET period_year = EXTRACT(YEAR FROM entry_date)::int, "
            "period_month = EXTRACT(MONTH FROM entry_date)::int"
        )
        op.execute(
            "UPDATE journal_entries SET status = CASE "
            "WHEN is_reversed THEN 'Reversed' "
            "WHEN is_posted THEN 'Posted' "
            "ELSE 'Draft' END"
        )
        op.execute(
            "UPDATE journal_entries SET source_type = COALESCE(NULLIF(source_module, ''), NULLIF(reference, ''), 'legacy')"
        )
        op.execute(
            "UPDATE journal_entries SET base_currency = COALESCE(NULLIF(currency_code, ''), base_currency, 'USD')"
        )
        op.execute(
            "UPDATE journal_entries SET entry_no = COALESCE(NULLIF(entry_no, ''), CONCAT('JE-', SUBSTR(id::text, 1, 12)))"
        )
        op.execute(
            "UPDATE journal_entries AS je "
            "SET total_debit_base = COALESCE(lines.debit_total, 0), "
            "total_credit_base = COALESCE(lines.credit_total, 0) "
            "FROM ("
            "SELECT journal_entry_id, SUM(debit) AS debit_total, SUM(credit) AS credit_total "
            "FROM journal_entry_lines GROUP BY journal_entry_id"
            ") AS lines "
            "WHERE je.id = lines.journal_entry_id"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("journal_entries"):
        op.drop_index("ix_journal_entries_entry_no", table_name="journal_entries")
        op.drop_index("ix_journal_entries_source_type_id", table_name="journal_entries")
        op.drop_index("ix_journal_entries_period_year_month", table_name="journal_entries")
        op.drop_index("ix_journal_entries_entry_date", table_name="journal_entries")

        with op.batch_alter_table("journal_entries") as batch:
            batch.drop_constraint("fk_journal_entries_approved_by", type_="foreignkey")
            batch.drop_constraint("fk_journal_entries_created_by", type_="foreignkey")
            batch.drop_constraint("fk_journal_entries_reversal_of", type_="foreignkey")
            batch.drop_column("posted_at")
            batch.drop_column("approved_by")
            batch.drop_column("created_by")
            batch.drop_column("reversal_of_entry_id")
            batch.drop_column("total_credit_base")
            batch.drop_column("total_debit_base")
            batch.drop_column("base_currency")
            batch.drop_column("memo")
            batch.drop_column("source_type")
            batch.drop_column("status")
            batch.drop_column("period_month")
            batch.drop_column("period_year")
            batch.drop_column("posting_date")
            batch.drop_column("entry_date")
            batch.drop_column("entry_no")

    if inspector.has_table("journal_lines"):
        op.drop_index("ix_journal_lines_account_id", table_name="journal_lines")
        op.drop_index("ix_journal_lines_entry_id", table_name="journal_lines")
        op.drop_index("ix_journal_lines_created_at", table_name="journal_lines")
        op.drop_index("ix_journal_lines_tenant_id", table_name="journal_lines")
        op.drop_table("journal_lines")

    if inspector.has_table("account_mappings"):
        op.drop_constraint("uq_account_mappings_tenant_key", "account_mappings", type_="unique")
        op.drop_index("ix_account_mappings_created_at", table_name="account_mappings")
        op.drop_index("ix_account_mappings_tenant_id", table_name="account_mappings")
        op.drop_table("account_mappings")

    if inspector.has_table("accounts"):
        op.drop_constraint("uq_accounts_tenant_code", "accounts", type_="unique")
        op.drop_index("ix_accounts_created_at", table_name="accounts")
        op.drop_index("ix_accounts_tenant_id", table_name="accounts")
        op.drop_table("accounts")
