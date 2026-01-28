"""Sprint 20 taxes + FX + revaluation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_sprint20_fx_tax"
down_revision = "0019_sprint19_settlements_ar_ap"
branch_labels = None
depends_on = None

fx_revaluation_status_enum = postgresql.ENUM(
    "POSTED",
    "REVERSED",
    name="fx_revaluation_status",
    create_type=False,
)


def upgrade() -> None:
    fx_revaluation_status_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("sales_invoices") as batch:
        batch.add_column(sa.Column("fx_rate", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("vat_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_subtotal", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_vat_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))

    with op.batch_alter_table("purchase_invoices") as batch:
        batch.add_column(sa.Column("fx_rate", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("vat_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_subtotal", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_vat_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))

    with op.batch_alter_table("sales_invoice_lines") as batch:
        batch.add_column(sa.Column("vat_rate", sa.Numeric(9, 4), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))

    with op.batch_alter_table("purchase_invoice_lines") as batch:
        batch.add_column(sa.Column("vat_rate", sa.Numeric(9, 4), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("base_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")))

    with op.batch_alter_table("customer_receipts") as batch:
        batch.add_column(sa.Column("fx_rate", sa.Numeric(18, 6), nullable=True))
        batch.add_column(
            sa.Column("base_amount_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0"))
        )

    with op.batch_alter_table("vendor_payments") as batch:
        batch.add_column(sa.Column("fx_rate", sa.Numeric(18, 6), nullable=True))
        batch.add_column(
            sa.Column("base_amount_total", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0"))
        )

    op.create_table(
        "fx_revaluation_runs",
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=False),
        sa.Column("reval_fx_rate", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "status",
            fx_revaluation_status_enum,
            nullable=False,
            server_default=sa.text("'POSTED'"),
        ),
        sa.Column("posting_journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["posting_journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "period_year",
            "period_month",
            "currency_code",
            name="uq_fx_revaluation_runs_tenant_period_currency",
        ),
    )
    op.create_index("ix_fx_revaluation_runs_tenant_id", "fx_revaluation_runs", ["tenant_id"], unique=False)
    op.create_index("ix_fx_revaluation_runs_created_at", "fx_revaluation_runs", ["created_at"], unique=False)
    op.create_index(
        "ix_fx_revaluation_runs_period",
        "fx_revaluation_runs",
        ["period_year", "period_month"],
        unique=False,
    )
    op.create_index("ix_fx_revaluation_runs_currency", "fx_revaluation_runs", ["currency_code"], unique=False)

    op.create_table(
        "fx_revaluation_lines",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("foreign_remaining", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("old_base_remaining", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("new_base_remaining", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("delta_base", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["fx_revaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fx_revaluation_lines_tenant_id", "fx_revaluation_lines", ["tenant_id"], unique=False)
    op.create_index("ix_fx_revaluation_lines_created_at", "fx_revaluation_lines", ["created_at"], unique=False)
    op.create_index("ix_fx_revaluation_lines_run_id", "fx_revaluation_lines", ["run_id"], unique=False)
    op.create_index("ix_fx_revaluation_lines_source", "fx_revaluation_lines", ["source_type", "source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fx_revaluation_lines_source", table_name="fx_revaluation_lines")
    op.drop_index("ix_fx_revaluation_lines_run_id", table_name="fx_revaluation_lines")
    op.drop_index("ix_fx_revaluation_lines_created_at", table_name="fx_revaluation_lines")
    op.drop_index("ix_fx_revaluation_lines_tenant_id", table_name="fx_revaluation_lines")
    op.drop_table("fx_revaluation_lines")

    op.drop_index("ix_fx_revaluation_runs_currency", table_name="fx_revaluation_runs")
    op.drop_index("ix_fx_revaluation_runs_period", table_name="fx_revaluation_runs")
    op.drop_index("ix_fx_revaluation_runs_created_at", table_name="fx_revaluation_runs")
    op.drop_index("ix_fx_revaluation_runs_tenant_id", table_name="fx_revaluation_runs")
    op.drop_table("fx_revaluation_runs")

    with op.batch_alter_table("vendor_payments") as batch:
        batch.drop_column("base_amount_total")
        batch.drop_column("fx_rate")

    with op.batch_alter_table("customer_receipts") as batch:
        batch.drop_column("base_amount_total")
        batch.drop_column("fx_rate")

    with op.batch_alter_table("purchase_invoice_lines") as batch:
        batch.drop_column("base_amount")
        batch.drop_column("vat_amount")
        batch.drop_column("vat_rate")

    with op.batch_alter_table("sales_invoice_lines") as batch:
        batch.drop_column("base_amount")
        batch.drop_column("vat_amount")
        batch.drop_column("vat_rate")

    with op.batch_alter_table("purchase_invoices") as batch:
        batch.drop_column("base_total")
        batch.drop_column("base_vat_total")
        batch.drop_column("base_subtotal")
        batch.drop_column("vat_total")
        batch.drop_column("fx_rate")

    with op.batch_alter_table("sales_invoices") as batch:
        batch.drop_column("base_total")
        batch.drop_column("base_vat_total")
        batch.drop_column("base_subtotal")
        batch.drop_column("vat_total")
        batch.drop_column("fx_rate")

    fx_revaluation_status_enum.drop(op.get_bind(), checkfirst=True)
