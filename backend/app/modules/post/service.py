"""Post queries and edits expressed exclusively through SQLAlchemy ORM models."""

import math
import uuid
from typing import Any

from sqlalchemy import delete as delete_rows
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, defer, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.common.exceptions import ConflictError, NotFoundError
from app.common.time import utc_now
from app.modules.post.content import render
from app.modules.post.models import (
    AdminPostRead,
    PostInput,
    PostOrm,
    PostRead,
    PostRedirect,
    PostRedirectOrm,
    PostStatistics,
    PostTagOrm,
)
from app.modules.tag.models import TagOrm, TagRead
from app.modules.tag.service import set_post_tags


def public_predicate() -> ColumnElement[bool]:
    return (PostOrm.status == "published") & (PostOrm.published_at <= utc_now())


def get_post(db_session: Session, post_id: str) -> PostOrm:
    record = db_session.get(PostOrm, post_id)
    if record is None:
        raise NotFoundError("Post not found", code="post.not_found")
    return record


def serialize(record: PostOrm, *, detail: bool = False, admin: bool = False) -> dict[str, Any]:
    fields = {
        name: getattr(record, name)
        for name in (
            "id",
            "slug",
            "title",
            "excerpt",
            "status",
            "type",
            "feature_image",
            "author",
            "author_slug",
            "created_at",
            "updated_at",
            "published_at",
            "version",
        )
    }
    fields["tags"] = [
        TagRead(id=link.tag.id, name=link.tag.name, slug=link.tag.slug).model_dump(
            exclude_none=True
        )
        for link in record.tag_links
    ]
    fields["reading_time"] = max(1, math.ceil(record.reading_characters / 600))
    if not admin and not record.excerpt:
        fields["excerpt"] = record.automatic_excerpt
    if admin:
        fields["format"] = record.format
        if detail:
            fields["body"] = record.body
    if detail:
        fields["html"] = record.html
    return fields


def list_posts(
    db_session: Session,
    *,
    page: int = 1,
    limit: int = 5,
    q: str = "",
    tag: str = "",
    author: str = "",
    status: str = "",
    kind: str = "post",
    admin: bool = False,
) -> dict[str, Any]:
    statement = select(PostOrm)
    if not admin:
        statement = statement.where(public_predicate())
    elif status:
        statement = statement.where(PostOrm.status == status)
    if kind:
        statement = statement.where(PostOrm.type == kind)
    if q:
        statement = statement.where(
            or_(
                PostOrm.title.contains(q, autoescape=True),
                PostOrm.plain_text.contains(q, autoescape=True),
            )
        )
    if tag:
        statement = statement.where(PostOrm.tag_links.any(PostTagOrm.tag.has(TagOrm.slug == tag)))
    if author:
        statement = statement.where(PostOrm.author_slug == author)
    total = db_session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    statement = statement.options(
        selectinload(PostOrm.tag_links).joinedload(PostTagOrm.tag),
        defer(PostOrm.body),
        defer(PostOrm.html),
        defer(PostOrm.plain_text),
    )
    statement = statement.order_by(
        func.coalesce(PostOrm.published_at, PostOrm.created_at).desc(), PostOrm.id.desc()
    )
    records = db_session.scalars(statement.limit(limit).offset((page - 1) * limit)).all()
    return {
        "items": [serialize(row, admin=admin) for row in records],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)),
    }


def save_post(
    db_session: Session,
    data: PostInput,
    post_id: str | None = None,
) -> AdminPostRead:
    previous = get_post(db_session, post_id) if post_id else None
    if previous and data.version != previous.version:
        raise ConflictError(
            "This post was updated in another window. Reload before saving.",
            code="post.version_conflict",
        )
    alias = db_session.get(PostRedirectOrm, data.slug)
    if alias and alias.post_id != post_id:
        raise ConflictError(
            "This URL is reserved by an existing post redirect", code="post.slug_reserved"
        )
    timestamp = utc_now()
    published = data.published_at or (previous.published_at if previous else None)
    if data.status == "published" and published is None:
        published = timestamp
    html, plain_text = render(data.body, data.format)
    values = data.model_dump(exclude={"tags", "version", "published_at"})
    values.update(html=html, plain_text=plain_text, updated_at=timestamp, published_at=published)
    try:
        if previous:
            old_slug = previous.slug
            result = db_session.execute(
                update(PostOrm)
                .where(PostOrm.id == post_id, PostOrm.version == data.version)
                .values(**values, version=PostOrm.version + 1)
            )
            if result.rowcount != 1:
                raise ConflictError(
                    "This post was updated in another window. Reload before saving.",
                    code="post.version_conflict",
                )
            if old_slug != data.slug:
                db_session.execute(
                    delete_rows(PostRedirectOrm).where(
                        PostRedirectOrm.slug == data.slug, PostRedirectOrm.post_id == post_id
                    )
                )
                existing_alias = db_session.get(PostRedirectOrm, old_slug)
                if existing_alias:
                    existing_alias.post_id = previous.id
                else:
                    db_session.add(PostRedirectOrm(slug=old_slug, post_id=previous.id))
            record = previous
        else:
            record = PostOrm(id=uuid.uuid4().hex, created_at=timestamp, version=1, **values)
            db_session.add(record)
        db_session.flush()
        set_post_tags(db_session, record.id, data.tags)
        db_session.flush()
        db_session.expire(record, ["tag_links", "reading_characters", "automatic_excerpt"])
        return AdminPostRead.model_validate(serialize(record, detail=True, admin=True))
    except IntegrityError as error:
        raise ConflictError("This post URL is already in use", code="post.slug_conflict") from error


def get_public(*, db_session: Session, slug: str) -> PostRead | PostRedirect:
    record = db_session.scalar(select(PostOrm).where(PostOrm.slug == slug, public_predicate()))
    if record is None:
        redirect = db_session.scalar(
            select(PostOrm.slug)
            .join(PostRedirectOrm)
            .where(PostRedirectOrm.slug == slug, public_predicate())
        )
        if redirect:
            return PostRedirect(redirect=redirect)
        raise NotFoundError(
            "This post does not exist or has not been published", code="post.not_found"
        )
    related = db_session.scalars(
        select(PostOrm)
        .options(defer(PostOrm.body), defer(PostOrm.html), defer(PostOrm.plain_text))
        .where(PostOrm.id != record.id, PostOrm.type == "post", public_predicate())
        .order_by(
            func.abs(func.julianday(PostOrm.published_at) - func.julianday(record.published_at))
        )
        .limit(2)
    ).all()
    return PostRead.model_validate(
        {
            **serialize(record, detail=True),
            "related": [serialize(item) for item in related],
        }
    )


def get_statistics(*, db_session: Session) -> PostStatistics:
    counts = dict(
        db_session.execute(select(PostOrm.status, func.count()).group_by(PostOrm.status)).all()
    )
    return PostStatistics(
        **counts,
        tags=db_session.scalar(select(func.count()).select_from(TagOrm)) or 0,
        total=sum(counts.values()),
    )


def delete(*, db_session: Session, post_id: str) -> None:
    db_session.delete(get_post(db_session, post_id))
