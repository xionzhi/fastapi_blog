from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.common.orm import Base, UTCDateTime
from app.modules.post.content import safe_url, validate_slug
from app.modules.tag.models import TagRead

if TYPE_CHECKING:
    from app.modules.tag.models import TagOrm


class PostInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    body: str = Field(default="", max_length=2_000_000)
    format: Literal["markdown", "html"] = "markdown"
    excerpt: str = Field(default="", max_length=1000)
    status: Literal["draft", "published"] = "draft"
    type: Literal["post", "page"] = "post"
    feature_image: str = Field(default="", max_length=2000)
    author: str = Field(default="xionzhi", min_length=1, max_length=100)
    author_slug: str = Field(default="xionzhi", min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=30)
    published_at: datetime | None = None
    version: int | None = Field(default=None, ge=1)

    @field_validator("published_at")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value

    @field_validator("title", "author")
    @classmethod
    def nonblank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be blank")
        return v.strip()

    @field_validator("slug", "author_slug")
    @classmethod
    def slug_valid(cls, v: str) -> str:
        return validate_slug(v)

    @field_validator("feature_image")
    @classmethod
    def url_valid(cls, v: str) -> str:
        return safe_url(v)

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, tags: list[str]) -> list[str]:
        if any(not t.strip() or len(t) > 80 for t in tags):
            raise ValueError("Tags must contain between 1 and 80 characters")
        return list(dict.fromkeys(t.strip() for t in tags))


class PreviewInput(BaseModel):
    body: str = Field(default="", max_length=2_000_000)
    format: Literal["markdown", "html"] = "markdown"


class PostSummary(BaseModel):
    id: str
    slug: str
    title: str
    excerpt: str
    status: Literal["draft", "published"]
    type: Literal["post", "page"]
    feature_image: str
    author: str
    author_slug: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    version: int
    reading_time: int
    tags: list[TagRead]


class PostRead(PostSummary):
    html: str
    related: list[PostSummary] = Field(default_factory=list)


class AdminPostSummary(PostSummary):
    format: Literal["markdown", "html"]


class AdminPostRead(AdminPostSummary):
    body: str
    html: str


class PostRedirect(BaseModel):
    redirect: str


class PreviewResponse(BaseModel):
    html: str


class PostStatistics(BaseModel):
    published: int = 0
    draft: int = 0
    tags: int = 0
    total: int = 0


class PostOrm(Base):
    __tablename__ = "posts"
    __table_args__ = (Index("posts_public", "status", "type", "published_at"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text, default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    format: Mapped[str] = mapped_column(String(16), default="markdown", server_default="markdown")
    html: Mapped[str] = mapped_column(Text, default="", server_default="")
    plain_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    reading_characters: Mapped[int] = column_property(func.length(plain_text))
    automatic_excerpt: Mapped[str] = column_property(func.substr(plain_text, 1, 220))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    type: Mapped[str] = mapped_column(String(16), default="post", server_default="post")
    feature_image: Mapped[str] = mapped_column(Text, default="", server_default="")
    author: Mapped[str] = mapped_column(String(100), default="xionzhi", server_default="xionzhi")
    author_slug: Mapped[str] = mapped_column(
        String(200), default="xionzhi", server_default="xionzhi"
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    tag_links: Mapped[list["PostTagOrm"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostTagOrm.position",
        lazy="selectin",
        passive_deletes=True,
    )
    redirects: Mapped[list["PostRedirectOrm"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )


class PostTagOrm(Base):
    __tablename__ = "posts_tags"
    post_id: Mapped[str] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    post: Mapped[PostOrm] = relationship(back_populates="tag_links")
    tag: Mapped["TagOrm"] = relationship(lazy="joined")


class PostRedirectOrm(Base):
    __tablename__ = "redirects"
    slug: Mapped[str] = mapped_column(String(200), primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    post: Mapped[PostOrm] = relationship(back_populates="redirects")
