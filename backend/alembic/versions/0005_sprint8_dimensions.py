"""Add dimensions and journal line dimension mappings (Sprint 8).

Revision ID: 0005_sprint8_dimensions
Revises: 0004_sprint4_permission_backfill
Create Date: 2026-01-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_sprint8_dimensions"
down_revision = "0004_sprint4_permission_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dimensions",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_dimensions_tenant_key"),
    )
    op.create_index("ix_dimensions_tenant_id", "dimensions", ["tenant_id"], unique=False)
    op.create_index("ix_dimensions_created_at", "dimensions", ["created_at"], unique=False)
    op.create_index("ix_dimensions_key", "dimensions", ["key"], unique=False)

    op.create_table(
        "dimension_values",
        sa.Column("dimension_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "dimension_id",
            "code",
            name="uq_dimension_values_tenant_dimension_code",
        ),
    )
    op.create_index("ix_dimension_values_tenant_id", "dimension_values", ["tenant_id"], unique=False)
    op.create_index("ix_dimension_values_dimension_id", "dimension_values", ["dimension_id"], unique=False)
    op.create_index("ix_dimension_values_created_at", "dimension_values", ["created_at"], unique=False)

    op.create_table(
        "journal_line_dimensions",
        sa.Column("journal_line_id", sa.UUID(), nullable=False),
        sa.Column("dimension_value_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("(uuid_generate_v4())"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["journal_line_id"], ["journal_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dimension_value_id"], ["dimension_values.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "journal_line_id",
            "dimension_value_id",
            name="uq_journal_line_dimension_value",
        ),
    )
    op.create_index("ix_journal_line_dimensions_tenant_id", "journal_line_dimensions", ["tenant_id"], unique=False)
    op.create_index(
        "ix_journal_line_dimensions_created_at",
        "journal_line_dimensions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_journal_line_dimensions_journal_line_id",
        "journal_line_dimensions",
        ["journal_line_id"],
        unique=False,
    )
    op.create_index(
        "ix_journal_line_dimensions_dimension_value_id",
        "journal_line_dimensions",
        ["dimension_value_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_journal_line_dimensions_dimension_value_id", table_name="journal_line_dimensions")
    op.drop_index("ix_journal_line_dimensions_journal_line_id", table_name="journal_line_dimensions")
    op.drop_index("ix_journal_line_dimensions_created_at", table_name="journal_line_dimensions")
    op.drop_index("ix_journal_line_dimensions_tenant_id", table_name="journal_line_dimensions")
    op.drop_table("journal_line_dimensions")

    op.drop_index("ix_dimension_values_created_at", table_name="dimension_values")
    op.drop_index("ix_dimension_values_dimension_id", table_name="dimension_values")
    op.drop_index("ix_dimension_values_tenant_id", table_name="dimension_values")
    op.drop_table("dimension_values")

    op.drop_index("ix_dimensions_key", table_name="dimensions")
    op.drop_index("ix_dimensions_created_at", table_name="dimensions")
    op.drop_index("ix_dimensions_tenant_id", table_name="dimensions")
    op.drop_table("dimensions")
