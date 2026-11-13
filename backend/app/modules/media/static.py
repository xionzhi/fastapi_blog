"""Serve image media types consistently across operating systems."""

from pathlib import PurePosixPath

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class ImageStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        media_type = IMAGE_MEDIA_TYPES.get(PurePosixPath(path).suffix.lower())
        if media_type and response.status_code == 200:
            response.headers["Content-Type"] = media_type
        return response
