"""Bounded anonymous daily traffic aggregates."""

import sqlalchemy as sa
from alembic import op

revision = "20261113_0002"
down_revision = "20261113_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_days",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("visitors", sa.Integer(), nullable=False),
    )
    op.create_table(
        "analytics_pages",
        sa.Column(
            "day",
            sa.Date(),
            sa.ForeignKey("analytics_days.day", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("path", sa.String(512), primary_key=True),
        sa.Column(
            "post_id", sa.String(32), sa.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("views", sa.Integer(), nullable=False),
    )
    op.create_index("ix_analytics_pages_post_id", "analytics_pages", ["post_id"])
    op.create_table(
        "analytics_visitors",
        sa.Column(
            "day",
            sa.Date(),
            sa.ForeignKey("analytics_days.day", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("visitor_hash", sa.String(64), primary_key=True),
        sa.Column("last_event_id", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_visitors")
    op.drop_table("analytics_pages")
    op.drop_table("analytics_days")
