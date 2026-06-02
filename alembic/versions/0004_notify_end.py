"""notify_end: items.notify_end + recurrences.notify_end

Revision ID: 0004_notify_end
Revises: 0003_event_end_time
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_notify_end"
down_revision = "0003_event_end_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("notify_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "recurrences",
        sa.Column("notify_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("recurrences", "notify_end")
    op.drop_column("items", "notify_end")
