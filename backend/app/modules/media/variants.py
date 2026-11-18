"""Bounded, disposable WebP derivatives of local images; originals are never modified."""

import hashlib
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings
from app.modules.media.models import ImageRead
from app.modules.media.service import MAX_IMAGE_BYTES, SUPPORTED_FORMATS
from app.modules.media.validation import valid_gif, webp_canvas_size

WIDTHS = (48, 96)
LIBRARY_WIDTH = 480
MAX_SOURCE_PIXELS = 40_000_000
MAX_DECODE_PIXELS = 12_000_000
ENCODERS = BoundedSemaphore(1)
IMAGE_ERRORS = (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError)


@contextmanager
def open_source(path: Path) -> Iterator[Image.Image]:
    with path.open("rb") as stream:
        header = stream.read(32)
        stream.seek(0)
        if header.startswith((b"GIF87a", b"GIF89a")):
            content = stream.read(MAX_IMAGE_BYTES + 1)
            if len(content) > MAX_IMAGE_BYTES or not valid_gif(
                content, max_pixels=MAX_SOURCE_PIXELS
            ):
                raise ValueError("GIF exceeds the preview budget or is invalid")
            stream.seek(0)
        elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            size = webp_canvas_size(header)
            if size is None or size[0] * size[1] > MAX_SOURCE_PIXELS:
                raise ValueError("WebP exceeds the preview budget or is invalid")
        with Image.open(stream, formats=list(SUPPORTED_FORMATS)) as image:
            yield image


def revision(path: Path) -> str:
    stat = path.stat()
    return hashlib.sha256(f"{stat.st_mtime_ns}:{stat.st_size}:webp-82-v1".encode()).hexdigest()[:32]


def describe(settings: Settings, url: str, role: str) -> ImageRead | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/content/images/"):
        return None
    try:
        path = (settings.images / unquote(parsed.path.removeprefix("/content/images/"))).resolve()
        if not path.is_relative_to(settings.images) or not path.is_file():
            return None
        if path.stat().st_size > MAX_IMAGE_BYTES:
            return None
        with open_source(path) as image:
            width, height = image.size
            if (image.format != "JPEG" and width * height > MAX_SOURCE_PIXELS) or getattr(
                image, "is_animated", False
            ):
                return None
            if image.getexif().get(274) in (5, 6, 7, 8):
                width, height = height, width
        version = revision(path)
    except IMAGE_ERRORS:
        return None

    def source(size: int) -> str:
        query = dict(parse_qsl(parsed.query))
        query.update(width=str(size), v=version)
        return urlunsplit(parsed._replace(query=urlencode(query)))

    if role != "avatar":
        return ImageRead(src=url, width=width, height=height)
    return ImageRead(
        src=source(48),
        width=width,
        height=height,
        srcset=f"{source(48)} {min(width, 48)}w, {source(96)} {min(width, 96)}w"
        if width > 48
        else "",
        sizes="24px",
    )


def variant(
    source: Path, cache: Path, width: int, *, preview: bool = False
) -> tuple[Path, str] | None:
    temporary = None
    try:
        if (
            width not in WIDTHS and not (preview and width == LIBRARY_WIDTH)
        ) or source.stat().st_size > MAX_IMAGE_BYTES:
            return None
        version = revision(source)
        key = hashlib.sha256(f"{source}:{version}:{width}:{preview}".encode()).hexdigest()
        target = cache / f"{key}.webp"
        if target.is_file():
            return target, version
        temporary = cache / f"{key}-{uuid.uuid4().hex}.tmp"
        with ENCODERS, open_source(source) as image:
            if getattr(image, "is_animated", False) and not preview:
                return None
            # JPEG draft decoding reduces memory before loading full-resolution pixels.
            image.draft("RGB", (width, width))
            if image.width * image.height > MAX_DECODE_PIXELS:
                return None
            ImageOps.exif_transpose(image, in_place=True)
            image.thumbnail(
                (width, width if preview else MAX_SOURCE_PIXELS), Image.Resampling.LANCZOS
            )
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            cache.mkdir(parents=True, exist_ok=True)
            image.save(temporary, format="WEBP", quality=82, method=4)
            os.replace(temporary, target)
        return target, version
    except IMAGE_ERRORS:
        return None
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
