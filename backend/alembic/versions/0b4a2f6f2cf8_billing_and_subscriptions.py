"""billing plans and subscriptions

Revision ID: 0b4a2f6f2cf8
Revises: c6b1e7e7260d
Create Date: 2025-12-06 21:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0b4a2f6f2cf8"
down_revision = "c6b1e7e7260d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="usd"),
        sa.Column("interval", sa.String(length=20), nullable=False, server_default="month"),
        sa.Column("limits_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_billing_plans_code"),
    )
    op.create_index("ix_billing_plans_code", "billing_plans", ["code"], unique=False)

    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("plan_code", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=120), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("checkout_session_id", sa.String(length=120), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("usage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant"),
    )
    op.create_index("ix_tenant_subscriptions_plan_code", "tenant_subscriptions", ["plan_code"], unique=False)
    op.create_index(
        "ix_tenant_subscriptions_stripe_customer", "tenant_subscriptions", ["stripe_customer_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_subscriptions_stripe_customer", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_plan_code", table_name="tenant_subscriptions")
    op.drop_table("tenant_subscriptions")

    op.drop_index("ix_billing_plans_code", table_name="billing_plans")
    op.drop_table("billing_plans")
