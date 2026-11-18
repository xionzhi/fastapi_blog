"""Image uploads, library queries, and usage-aware filesystem operations."""

import hashlib
import logging
import math
import os
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

from PIL import UnidentifiedImageError
from sqlalchemy.orm import Session

from app.common.database import begin_write
from app.common.exceptions import ApplicationError, ConflictError, NotFoundError
from app.core.config import Settings
from app.modules.media.models import (
    ImageLibrary,
    ImageMove,
    ImageMoveResult,
    ImageSelection,
    ImageUsage,
    LibraryImage,
    UploadedImage,
)
from app.modules.media.references import find_usages, image_url, reference_key, update_references
from app.modules.media.validation import image_format

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
logger = logging.getLogger("blog.media")


def save_image(*, settings: Settings, content: bytes) -> UploadedImage:
    if len(content) > MAX_IMAGE_BYTES:
        raise ApplicationError(
            "Images must not exceed 20 MB", code="media.too_large", status_code=413
        )
    try:
        extension = SUPPORTED_FORMATS[image_format(content)]
    except UnidentifiedImageError as exc:
        raise ApplicationError(
            "Choose a valid PNG, JPEG, WebP, or GIF image",
            code="media.invalid_image",
            status_code=422,
        ) from exc
    relative_path = f"{datetime.now().strftime('%Y/%m')}/{uuid.uuid4().hex}.{extension}"
    path = image_path(settings, relative_path)
    created = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            created = True
            stream.write(content)
    except OSError as error:
        if created:
            with suppress(OSError):
                path.unlink()
        raise ApplicationError(
            "The image could not be saved. Check storage space and directory permissions.",
            code="media.upload_failed",
            status_code=409,
        ) from error
    return UploadedImage(url="/content/images/" + relative_path)


def image_path(settings: Settings, relative: str) -> Path:
    parts = relative.split("/")
    if (
        not relative
        or len(relative) > 500
        or any(not part or part.startswith(".") or part.endswith((" ", ".")) for part in parts)
        or any(len(part.encode("utf-8")) > 240 for part in parts)
        or any(character in relative for character in '\\:\x00<>"|?*%#')
        or any(ord(character) < 32 for character in relative)
        or PurePosixPath(relative).suffix.lower() not in EXTENSIONS
    ):
        raise ApplicationError(
            "Use an image path such as 2026/11/photo.png, without hidden or parent directories.",
            code="media.invalid_path",
            status_code=422,
        )
    path = settings.images
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ApplicationError("Symbolic links cannot be managed", code="media.unsafe_path")
    resolved = path.resolve()
    if not resolved.is_relative_to(settings.images):
        raise ApplicationError("Invalid image path", code="media.unsafe_path")
    return resolved


def file_revision(path: Path) -> str:
    stat = path.stat()
    return hashlib.sha256(
        f"{stat.st_dev}:{stat.st_ino}:{stat.st_mtime_ns}:{stat.st_size}".encode()
    ).hexdigest()[:32]


def describe_image(
    settings: Settings, path: Path, usages: list[ImageUsage] | None = None
) -> LibraryImage:
    relative = path.relative_to(settings.images).as_posix()
    stat = path.stat()
    revision = file_revision(path)
    return LibraryImage(
        path=relative,
        name=path.name,
        url=image_url(relative),
        thumbnail="/api/admin/images/thumbnail?" + urlencode({"path": relative, "v": revision}),
        size=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, UTC),
        revision=revision,
        usages=usages or [],
    )


def list_images(
    *, session: Session, settings: Settings, q: str, page: int, limit: int
) -> ImageLibrary:
    files = []
    for directory, folders, names in os.walk(settings.images, followlinks=False):
        folders[:] = [
            name
            for name in folders
            if not name.startswith(".") and not (Path(directory) / name).is_symlink()
        ]
        for name in names:
            path = Path(directory) / name
            relative = path.relative_to(settings.images).as_posix()
            if path.suffix.lower() not in EXTENSIONS or q.casefold() not in relative.casefold():
                continue
            try:
                checked = image_path(settings, relative)
                if checked.is_file():
                    files.append((checked.stat().st_mtime_ns, relative, checked))
            except (ApplicationError, OSError):
                continue
    files.sort(key=lambda item: (-item[0], item[1]))
    usages = find_usages(session, settings)
    items = []
    for _, relative, path in files[(page - 1) * limit : page * limit]:
        try:
            items.append(describe_image(settings, path, usages.get(reference_key(relative))))
        except FileNotFoundError:
            continue  # A concurrent deletion must not fail the whole library.
    return ImageLibrary(
        items=items,
        total=len(files),
        page=page,
        limit=limit,
        pages=max(1, math.ceil(len(files) / limit)),
    )


def checked_image(settings: Settings, selection: ImageSelection) -> Path:
    path = image_path(settings, selection.path)
    if not path.is_file():
        raise NotFoundError("This image no longer exists", code="media.not_found")
    if path.relative_to(settings.images).as_posix() != selection.path:
        raise ConflictError(
            "Refresh the library and use the current image path.", code="media.changed"
        )
    if file_revision(path) != selection.revision:
        raise ConflictError("This image changed. Refresh the library first.", code="media.changed")
    return path


def move_image(*, session: Session, settings: Settings, data: ImageMove) -> ImageMoveResult:
    begin_write(session)
    source = checked_image(settings, data)
    target = image_path(settings, data.new_path)
    if data.path == data.new_path:
        return ImageMoveResult(
            image=describe_image(
                settings, source, find_usages(session, settings).get(reference_key(data.path))
            )
        )
    if source.suffix.lower() != target.suffix.lower():
        raise ApplicationError(
            "Keep the existing file extension. Renaming does not convert image formats.",
            code="media.extension_changed",
            status_code=422,
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # An atomic, exclusive link keeps the original readable until references are committed.
        os.link(source, target)
    except FileExistsError as error:
        raise ConflictError(
            "An image already exists at that path", code="media.path_taken"
        ) from error
    except OSError as error:
        raise ApplicationError(
            "The image could not be moved. Check directory permissions and filesystem support.",
            code="media.move_failed",
            status_code=409,
        ) from error
    try:
        update_references(session, settings, data.path, data.new_path)
        session.flush()
        usages = find_usages(session, settings)
        if usages.get(reference_key(data.path)):
            raise ConflictError(
                "Some saved references could not be updated. Edit them before moving this image.",
                code="media.references_unsupported",
            )
        result = ImageMoveResult(
            image=describe_image(settings, target, usages.get(reference_key(data.new_path)))
        )
        session.commit()
    except Exception:
        session.rollback()
        try:
            target.unlink(missing_ok=True)
        except OSError:
            logger.warning("Image move rolled back; unreferenced destination file was retained")
        raise
    try:
        source.unlink()
    except OSError:
        result.source_retained = True
        logger.warning("Image moved; original file could not be removed")
    return result


def delete_image(*, session: Session, settings: Settings, data: ImageSelection) -> None:
    begin_write(session)
    path = checked_image(settings, data)
    if find_usages(session, settings).get(reference_key(data.path)):
        raise ConflictError(
            "This image is used by saved content. Remove its references before deleting it.",
            code="media.in_use",
        )
    try:
        path.unlink()
    except OSError as error:
        raise ApplicationError(
            "The image could not be deleted. Check directory permissions.",
            code="media.delete_failed",
            status_code=409,
        ) from error
