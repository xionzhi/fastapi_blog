"""Versioned native content format; no account or infrastructure configuration."""

from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.post.content import validate_slug
from app.modules.post.models import PostInput
from app.modules.site.models import SiteInput
from app.modules.tag.models import TagInput

Identifier = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
MAX_JSON_BYTES = 16 * 1024 * 1024


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or path.as_posix() != value
        or any(part.startswith(".") for part in path.parts)
        or any(c in value for c in '\\:\x00<>"|?*')
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Use a normalized project-relative path without traversal")
    return value


class NativePost(PostInput):
    model_config = ConfigDict(extra="forbid")
    id: Identifier
    tags: list[Identifier] = Field(default_factory=list, max_length=30)
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timezone_aware_metadata(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class NativeTag(TagInput):
    model_config = ConfigDict(extra="forbid")
    id: Identifier


class NativeRedirect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    post_id: Identifier
    _slug = field_validator("slug")(validate_slug)


class NativeFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(max_length=1200)
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    _path = field_validator("path")(relative_path)


class NativeExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["xionzhi-blog"]
    version: Literal[1]
    exported_at: datetime
    media_root: str = Field(max_length=1000)
    posts: list[NativePost] = Field(max_length=10000)
    tags: list[NativeTag] = Field(max_length=10000)
    redirects: list[NativeRedirect] = Field(default_factory=list, max_length=20000)
    site: SiteInput
    files: list[NativeFile] = Field(default_factory=list, max_length=10000)
    _media_root = field_validator("media_root")(relative_path)

    @model_validator(mode="after")
    def consistent_references(self) -> Self:
        if PurePosixPath(self.media_root).name != "images":
            raise ValueError("The media root must identify an images directory")
        for values in (
            [p.id for p in self.posts],
            [p.slug for p in self.posts],
            [t.id for t in self.tags],
            [t.slug for t in self.tags],
            [r.slug for r in self.redirects],
            [f.path.casefold() for f in self.files],
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate records are not allowed")
        tag_ids = {t.id for t in self.tags}
        post_ids = {p.id for p in self.posts}
        post_slugs = {p.slug for p in self.posts}
        for post in self.posts:
            if not set(post.tags) <= tag_ids or len(post.tags) != len(set(post.tags)):
                raise ValueError("Post tags must reference unique tags in this export")
        for redirect in self.redirects:
            if redirect.post_id not in post_ids or redirect.slug in post_slugs:
                raise ValueError("Invalid post redirect")
        for file in self.files:
            if not file.path.startswith(self.media_root + "/"):
                raise ValueError("File paths must be inside the exported media root")
        return self


class ImportPreview(BaseModel):
    sha256: str
    posts: int
    pages: int
    tags: int
    files: int
    ignored_files: int = 0
    new_posts: int = 0
    skipped_posts: int = 0
    new_tags: int = 0
    missing_files: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    can_import: bool = True


class ImportResult(BaseModel):
    imported_posts: int
    imported_tags: int
    skipped_posts: int
    settings_imported: bool
