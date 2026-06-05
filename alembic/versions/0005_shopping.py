"""shopping_items table

Revision ID: 0005_shopping
Revises: 0004_notify_end
Create Date: 2026-06-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_shopping"
down_revision = "0004_notify_end"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("shopping_items")
