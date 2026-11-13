"""Validated local image storage; request parsing belongs to the HTTP adapter."""

import io
import uuid
from datetime import datetime

from PIL import Image, UnidentifiedImageError

from app.common.exceptions import ApplicationError
from app.core.config import Settings
from app.modules.media.models import UploadedImage

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
SUPPORTED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


def save_image(*, settings: Settings, content: bytes) -> UploadedImage:
    if len(content) > MAX_IMAGE_BYTES:
        raise ApplicationError(
            "Images must not exceed 20 MB", code="media.too_large", status_code=413
        )
    try:
        with Image.open(io.BytesIO(content), formats=list(SUPPORTED_FORMATS)) as image:
            extension = SUPPORTED_FORMATS.get(image.format or "")
            if not extension or image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("Unsupported image")
            image.verify()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
        raise ApplicationError(
            "Choose a valid PNG, JPEG, WebP, or GIF image (up to 40 megapixels)",
            code="media.invalid_image",
            status_code=422,
        ) from exc
    relative_path = f"{datetime.now().strftime('%Y/%m')}/{uuid.uuid4().hex}.{extension}"
    path = settings.images / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return UploadedImage(url="/content/images/" + relative_path)
