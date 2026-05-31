"""recurrences table + items.recurrence_id

Revision ID: 0002_recurrences
Revises: 0001_initial
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_recurrences"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurrences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("time", sa.Time(), nullable=True),
        sa.Column("freq", sa.Text(), nullable=False),
        sa.Column("weekdays", sa.Text(), nullable=True),
        sa.Column("month_day", sa.Integer(), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("materialized_through", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column("items", sa.Column("recurrence_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_items_recurrence",
        "items",
        "recurrences",
        ["recurrence_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_items_recurrence", "items", type_="foreignkey")
    op.drop_column("items", "recurrence_id")
    op.drop_table("recurrences")
