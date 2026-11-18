"""Validate image structure without allocating a pixel buffer."""

from collections.abc import Iterator
from io import BytesIO
from struct import error as StructError

from PIL import JpegImagePlugin, PngImagePlugin, UnidentifiedImageError


def image_format(content: bytes) -> str:
    try:
        if content.startswith(b"\xff\xd8\xff"):
            with JpegImagePlugin.jpeg_factory(BytesIO(content)) as image:
                if image.format == "JPEG":
                    image.verify()
                    return "JPEG"
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):
            with PngImagePlugin.PngImageFile(BytesIO(content)) as image:
                image.verify()
            return "PNG"
        elif content.startswith((b"GIF87a", b"GIF89a")) and valid_gif(content):
            return "GIF"
        elif content.startswith(b"RIFF") and content[8:12] == b"WEBP" and valid_webp(content):
            return "WEBP"
    except (EOFError, IndexError, OSError, StructError, SyntaxError, TypeError, ValueError) as exc:
        raise UnidentifiedImageError("Invalid image data") from exc
    raise UnidentifiedImageError("Invalid or unsupported image format")


def gif_color_table_size(flags: int) -> int:
    return (6 << (flags & 7)) if flags & 0x80 else 0


def valid_gif(content: bytes, *, max_pixels: int | None = None) -> bool:
    if len(content) < 13:
        return False
    width = int.from_bytes(content[6:8], "little")
    height = int.from_bytes(content[8:10], "little")
    if not width or not height or (max_pixels is not None and width * height > max_pixels):
        return False
    offset = 13 + gif_color_table_size(content[10])
    has_image = False
    while offset < len(content):
        marker = content[offset : offset + 1]
        if marker == b";":
            return has_image
        if marker == b"!":
            offset += 2
        elif marker == b"," and offset + 10 < len(content):
            left = int.from_bytes(content[offset + 1 : offset + 3], "little")
            top = int.from_bytes(content[offset + 3 : offset + 5], "little")
            frame_width = int.from_bytes(content[offset + 5 : offset + 7], "little")
            frame_height = int.from_bytes(content[offset + 7 : offset + 9], "little")
            width = max(width, left + frame_width)
            height = max(height, top + frame_height)
            if (
                not frame_width
                or not frame_height
                or (max_pixels is not None and width * height > max_pixels)
            ):
                return False
            offset += 10 + gif_color_table_size(content[offset + 9])
            if (
                offset + 1 >= len(content)
                or not 1 <= content[offset] <= 8
                or not content[offset + 1]
            ):
                return False
            offset += 1
            has_image = True
        else:
            return False
        while offset < len(content) and content[offset]:
            offset += 1 + content[offset]
        offset += 1
    return False


def webp_chunks(data: memoryview, start: int, end: int) -> Iterator[tuple[bytes, memoryview]]:
    while start + 8 <= end:
        size = int.from_bytes(data[start + 4 : start + 8], "little")
        payload_start = start + 8
        next_chunk = payload_start + size + (size & 1)
        if next_chunk > end:
            raise ValueError("Truncated WebP chunk")
        yield bytes(data[start : start + 4]), data[payload_start : payload_start + size]
        start = next_chunk
    if start != end:
        raise ValueError("Truncated WebP chunk header")


def webp_frame_size(kind: bytes, data: memoryview) -> tuple[int, int] | None:
    if kind == b"VP8 " and len(data) > 10 and not data[0] & 1 and data[3:6] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[6:8], "little") & 0x3FFF
        height = int.from_bytes(data[8:10], "little") & 0x3FFF
        if width and height:
            return width, height
    if kind == b"VP8L" and len(data) > 5 and data[0] == 0x2F and data[4] >> 5 == 0:
        bits = int.from_bytes(data[1:5], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def webp_canvas_size(header: bytes) -> tuple[int, int] | None:
    kind = header[12:16]
    if kind == b"VP8X" and len(header) >= 30 and int.from_bytes(header[16:20], "little") == 10:
        width = int.from_bytes(header[24:27], "little") + 1
        height = int.from_bytes(header[27:30], "little") + 1
        return width, height
    return webp_frame_size(kind, memoryview(header)[20:])


def valid_webp(content: bytes) -> bool:
    end = 8 + int.from_bytes(content[4:8], "little")
    if not 20 <= end <= len(content) or webp_canvas_size(content[:32]) is None:
        return False
    has_image = False
    for kind, data in webp_chunks(memoryview(content), 12, end):
        if kind == b"ANMF":
            has_frame = False
            for frame_kind, frame_data in webp_chunks(data, 16, len(data)):
                has_frame |= webp_frame_size(frame_kind, frame_data) is not None
            if not has_frame:
                return False
            has_image = True
        else:
            has_image |= webp_frame_size(kind, data) is not None
    return has_image
