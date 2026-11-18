"""Opt-in sharing for saved drafts."""

import sqlalchemy as sa
from alembic import op

revision = "20261118_0003"
down_revision = "20261113_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("preview_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("posts", "preview_shared")
