"""Public tag collections and protected administrator tag operations."""

from fastapi import APIRouter, Response, status

from app.core.dependencies import DbSession
from app.modules.tag import service
from app.modules.tag.models import TagInput, TagRead

router = APIRouter(tags=["tags"])
admin_router = APIRouter(prefix="/tags", tags=["admin tags"])


@router.get("/tags", response_model=list[TagRead], response_model_exclude_none=True)
def list_public_tags(db_session: DbSession) -> list[TagRead]:
    return [TagRead.model_validate(item) for item in service.list_tags(db_session)]


@admin_router.get("", response_model=list[TagRead])
def list_admin_tags(db_session: DbSession) -> list[TagRead]:
    return [TagRead.model_validate(item) for item in service.list_tags(db_session, admin=True)]


@admin_router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagInput, db_session: DbSession) -> TagRead:
    return service.create(db_session=db_session, data=data)


@admin_router.put("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: str, data: TagInput, db_session: DbSession) -> TagRead:
    return service.update(db_session=db_session, tag_id=tag_id, data=data)


@admin_router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: str, db_session: DbSession) -> Response:
    service.delete(db_session=db_session, tag_id=tag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
