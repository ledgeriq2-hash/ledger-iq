"""Add composite indexes for invoice/report performance

Revision ID: adb123456789
Revises: fe12ab34cd56
Create Date: 2025-12-26 12:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "adb123456789"
down_revision = "fe12ab34cd56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_invoices_tenant_id_issue_date",
        "invoices",
        ["tenant_id", "issue_date"],
        unique=False,
    )
    op.create_index(
        "ix_journal_entries_tenant_id_date",
        "journal_entries",
        ["tenant_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_journal_entry_lines_tenant_journal",
        "journal_entry_lines",
        ["tenant_id", "journal_entry_id"],
        unique=False,
    )
    op.create_index(
        "ix_journal_entry_lines_tenant_account",
        "journal_entry_lines",
        ["tenant_id", "account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_journal_entry_lines_tenant_account", table_name="journal_entry_lines")
    op.drop_index("ix_journal_entry_lines_tenant_journal", table_name="journal_entry_lines")
    op.drop_index("ix_journal_entries_tenant_id_date", table_name="journal_entries")
    op.drop_index("ix_invoices_tenant_id_issue_date", table_name="invoices")
