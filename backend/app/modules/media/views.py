"""Bounded upload reading followed by image validation in a worker thread."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, Response

from app.common.exceptions import NotFoundError
from app.core.dependencies import DbSession, SettingsDependency
from app.modules.auth.dependencies import get_current_user
from app.modules.media import service
from app.modules.media.models import (
    ImageLibrary,
    ImageMove,
    ImageMoveResult,
    ImageSelection,
    UploadedImage,
)
from app.modules.media.variants import LIBRARY_WIDTH, variant

router = APIRouter(
    prefix="/admin/images", tags=["admin media"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=ImageLibrary)
def list_images(
    settings: SettingsDependency,
    db_session: DbSession,
    q: Annotated[str, Query(max_length=200)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=48)] = 24,
) -> ImageLibrary:
    return service.list_images(session=db_session, settings=settings, q=q, page=page, limit=limit)


@router.get("/thumbnail")
def thumbnail(
    settings: SettingsDependency, path: Annotated[str, Query(min_length=1, max_length=500)]
) -> FileResponse:
    source = service.image_path(settings, path)
    result = variant(source, settings.data_dir / "image-cache", LIBRARY_WIDTH, preview=True)
    if result is None:
        raise NotFoundError("Image preview is unavailable", code="media.preview_unavailable")
    return FileResponse(result[0], media_type="image/webp")


@router.put("", response_model=ImageMoveResult)
def move_image(
    data: ImageMove, settings: SettingsDependency, db_session: DbSession
) -> ImageMoveResult:
    return service.move_image(session=db_session, settings=settings, data=data)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    data: ImageSelection, settings: SettingsDependency, db_session: DbSession
) -> Response:
    service.delete_image(session=db_session, settings=settings, data=data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=UploadedImage, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, settings: SettingsDependency) -> UploadedImage:
    try:
        content = await file.read(service.MAX_IMAGE_BYTES + 1)
    finally:
        await file.close()
    return await run_in_threadpool(service.save_image, settings=settings, content=content)
