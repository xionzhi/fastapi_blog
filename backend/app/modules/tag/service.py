"""Tag dictionary and ordered associations, using mapped models only."""

import uuid
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy import delete as delete_rows
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import ConflictError, NotFoundError
from app.common.time import utc_now
from app.modules.post.content import slugify
from app.modules.tag.models import TagInput, TagOrm, TagRead


def set_post_tags(db_session: Session, post_id: str, names: list[str]) -> None:
    from app.modules.post.models import PostTagOrm

    db_session.execute(delete_rows(PostTagOrm).where(PostTagOrm.post_id == post_id))
    known = set()
    for position, name in enumerate(names):
        slug = slugify(name) or uuid.uuid4().hex[:8]
        tag = db_session.scalar(
            select(TagOrm)
            .where(or_(func.lower(TagOrm.name) == name.lower(), TagOrm.slug == slug))
            .order_by(case((func.lower(TagOrm.name) == name.lower(), 0), else_=1))
            .limit(1)
        )
        if tag is None:
            tag = TagOrm(id=uuid.uuid4().hex, name=name, slug=slug, description="")
            db_session.add(tag)
            db_session.flush()
        if tag.id not in known:
            db_session.add(PostTagOrm(post_id=post_id, tag_id=tag.id, position=position))
            known.add(tag.id)


def list_tags(db_session: Session, *, admin: bool = False) -> list[dict[str, Any]]:
    from app.modules.post.models import PostOrm, PostTagOrm

    predicate = PostOrm.id == PostTagOrm.post_id
    if not admin:
        predicate = and_(
            predicate,
            PostOrm.status == "published",
            PostOrm.type == "post",
            PostOrm.published_at <= utc_now(),
        )
    statement = (
        select(TagOrm, func.count(PostOrm.id).label("count"))
        .outerjoin(PostTagOrm, PostTagOrm.tag_id == TagOrm.id)
        .outerjoin(PostOrm, predicate)
        .group_by(TagOrm.id)
        .order_by(func.count(PostOrm.id).desc(), TagOrm.name)
    )
    return [
        TagRead(
            id=tag.id, name=tag.name, slug=tag.slug, description=tag.description, count=count
        ).model_dump()
        for tag, count in db_session.execute(statement)
        if admin or count
    ]


def create(*, db_session: Session, data: TagInput) -> TagRead:
    tag = TagOrm(id=uuid.uuid4().hex, **data.model_dump())
    db_session.add(tag)
    try:
        db_session.flush()
    except IntegrityError as error:
        raise ConflictError("This tag URL is already in use", code="tag.slug_conflict") from error
    return TagRead(id=tag.id, **data.model_dump(), count=0)


def update(*, db_session: Session, tag_id: str, data: TagInput) -> TagRead:
    tag = db_session.get(TagOrm, tag_id)
    if tag is None:
        raise NotFoundError("Tag not found", code="tag.not_found")
    for name, value in data.model_dump().items():
        setattr(tag, name, value)
    try:
        db_session.flush()
    except IntegrityError as error:
        raise ConflictError("This tag URL is already in use", code="tag.slug_conflict") from error
    return TagRead(id=tag.id, **data.model_dump())


def delete(*, db_session: Session, tag_id: str) -> None:
    tag = db_session.get(TagOrm, tag_id)
    if tag is not None:
        db_session.delete(tag)
