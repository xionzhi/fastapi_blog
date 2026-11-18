"""Bounded upload reading followed by image validation in a worker thread."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.responses import FileResponse, Response

from app.common.exceptions import ApplicationError, NotFoundError
from app.core.dependencies import DbSession, SettingsDependency
from app.modules.media import service
from app.modules.media.models import (
    ImageLibrary,
    ImageMove,
    ImageMoveResult,
    ImageSelection,
    UploadedImage,
)
from app.modules.media.variants import LIBRARY_WIDTH, variant

router = APIRouter(prefix="/images", tags=["admin media"])


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


@router.post(
    "",
    response_model=UploadedImage,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
async def upload_image(request: Request, settings: SettingsDependency) -> UploadedImage:
    # Parse multipart only after the administrator dependencies have accepted the request.
    async with request.form(max_files=1, max_fields=0) as form:
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ApplicationError(
                "Choose an image file", code="media.missing_file", status_code=422
            )
        content = await file.read(service.MAX_IMAGE_BYTES + 1)
    return await run_in_threadpool(service.save_image, settings=settings, content=content)
