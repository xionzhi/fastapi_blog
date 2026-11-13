"""Bounded upload reading followed by image validation in a worker thread."""

from fastapi import APIRouter, Depends, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import SettingsDependency
from app.modules.auth.dependencies import get_current_user
from app.modules.media import service
from app.modules.media.models import UploadedImage

router = APIRouter(
    prefix="/admin/images", tags=["admin media"], dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=UploadedImage, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, settings: SettingsDependency) -> UploadedImage:
    try:
        content = await file.read(service.MAX_IMAGE_BYTES + 1)
    finally:
        await file.close()
    return await run_in_threadpool(service.save_image, settings=settings, content=content)
