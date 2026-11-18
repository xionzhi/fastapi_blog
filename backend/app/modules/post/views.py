"""Explicit, typed route declarations for public and administrator posts."""

from fastapi import APIRouter, Depends, Query, Response, status

from app.common.exceptions import NotFoundError
from app.common.models import Page
from app.core.dependencies import DbSession
from app.modules.auth.dependencies import get_current_user
from app.modules.post import service
from app.modules.post.content import render
from app.modules.post.models import (
    AdminPostRead,
    AdminPostSummary,
    PostInput,
    PostRead,
    PostRedirect,
    PostStatistics,
    PostSummary,
    PreviewInput,
    PreviewResponse,
    PreviewSharing,
)

router = APIRouter(tags=["posts"])
admin_router = APIRouter(
    prefix="/admin", tags=["admin posts"], dependencies=[Depends(get_current_user)]
)


@router.get("/posts", response_model=Page[PostSummary])
def list_public_posts(
    db_session: DbSession,
    page: int = Query(default=1, ge=1, le=1_000_000_000),
    limit: int = Query(default=5, ge=1, le=100),
    q: str = Query(default="", max_length=200),
    tag: str = "",
    author: str = "",
) -> Page[PostSummary]:
    result = service.list_posts(db_session, page=page, limit=limit, q=q, tag=tag, author=author)
    return Page[PostSummary].model_validate(result)


@router.get("/posts/{slug}", response_model=PostRead | PostRedirect)
def get_public_post(slug: str, db_session: DbSession) -> PostRead | PostRedirect:
    return service.get_public(db_session=db_session, slug=slug)


@router.get("/preview/{post_id}", response_model=PostRead, include_in_schema=False)
def get_draft_preview(post_id: str, db_session: DbSession) -> PostRead:
    post = service.get_shared_preview(db_session, post_id)
    if post is None:
        raise NotFoundError("This preview is unavailable", code="post.preview_unavailable")
    return post


@admin_router.get("/stats", response_model=PostStatistics)
def get_post_statistics(db_session: DbSession) -> PostStatistics:
    return service.get_statistics(db_session=db_session)


@admin_router.get("/posts", response_model=Page[AdminPostSummary])
def list_admin_posts(
    db_session: DbSession,
    page: int = Query(default=1, ge=1, le=1_000_000_000),
    limit: int = Query(default=20, ge=1, le=100),
    q: str = Query(default="", max_length=200),
    status_filter: str = Query(default="", alias="status", pattern="^(draft|published)?$"),
    content_type: str = Query(default="", alias="type", pattern="^(post|page)?$"),
) -> Page[AdminPostSummary]:
    result = service.list_posts(
        db_session, page=page, limit=limit, q=q, status=status_filter, kind=content_type, admin=True
    )
    return Page[AdminPostSummary].model_validate(result)


@admin_router.get("/posts/{post_id}", response_model=AdminPostRead)
def get_admin_post(post_id: str, db_session: DbSession) -> AdminPostRead:
    record = service.get_post(db_session, post_id)
    return AdminPostRead.model_validate(service.serialize(record, detail=True, admin=True))


@admin_router.post("/posts", response_model=AdminPostRead, status_code=status.HTTP_201_CREATED)
def create_post(data: PostInput, db_session: DbSession) -> AdminPostRead:
    return AdminPostRead.model_validate(service.save_post(db_session, data))


@admin_router.put("/posts/{post_id}", response_model=AdminPostRead)
def update_post(post_id: str, data: PostInput, db_session: DbSession) -> AdminPostRead:
    return AdminPostRead.model_validate(service.save_post(db_session, data, post_id))


@admin_router.put("/posts/{post_id}/preview", response_model=PreviewSharing)
def set_draft_preview(post_id: str, data: PreviewSharing, db_session: DbSession) -> PreviewSharing:
    service.set_preview_sharing(db_session, post_id, enabled=data.enabled)
    return data


@admin_router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: str, db_session: DbSession) -> Response:
    service.delete(db_session=db_session, post_id=post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.post("/preview", response_model=PreviewResponse)
def preview_post(data: PreviewInput) -> PreviewResponse:
    return PreviewResponse(html=render(data.body, data.format)[0])
