"""Initial application schema."""

import sqlalchemy as sa
from alembic import op

revision = "20261113_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, server_default=""),
    )
    users = sa.table("users", sa.column("email"))
    op.create_index(
        "users_email_unique",
        "users",
        [users.c.email.collate("NOCASE")],
        unique=True,
        sqlite_where=users.c.email != "",
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "login_attempts",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("reset_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "password_resets",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_table(
        "posts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        *[
            sa.Column(name, sa.Text(), nullable=False, server_default="")
            for name in ("excerpt", "body", "html", "plain_text", "feature_image")
        ],
        sa.Column("format", sa.String(16), nullable=False, server_default="markdown"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("type", sa.String(16), nullable=False, server_default="post"),
        sa.Column("author", sa.String(100), nullable=False, server_default="xionzhi"),
        sa.Column("author_slug", sa.String(200), nullable=False, server_default="xionzhi"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("posts_public", "posts", ["status", "type", "published_at"])
    op.create_table(
        "tags",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "posts_tags",
        sa.Column(
            "post_id",
            sa.String(32),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id", sa.String(32), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "redirects",
        sa.Column("slug", sa.String(200), primary_key=True),
        sa.Column(
            "post_id", sa.String(32), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
        ),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "settings",
        "redirects",
        "posts_tags",
        "tags",
        "posts",
        "password_resets",
        "login_attempts",
        "sessions",
        "users",
    ):
        op.drop_table(table)
