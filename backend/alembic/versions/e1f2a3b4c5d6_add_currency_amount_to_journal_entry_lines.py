"""add currency amount to journal entry lines"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("journal_entry_lines") as batch:
        batch.add_column(sa.Column("currency_amount", sa.Numeric(18, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("journal_entry_lines") as batch:
        batch.drop_column("currency_amount")
