"""Serve image media types consistently across operating systems."""

from pathlib import Path, PurePosixPath

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import QueryParams
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.modules.media.variants import WIDTHS, variant

IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class ImageStaticFiles(StaticFiles):
    def __init__(self, *, cache: Path, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.cache = cache

    async def get_response(self, path: str, scope: Scope) -> Response:
        query = QueryParams(scope.get("query_string", b""))
        if "width" in query:
            if query["width"] not in {str(width) for width in WIDTHS}:
                return Response("Unsupported image width", status_code=400)
            full_path, stat = await run_in_threadpool(self.lookup_path, path)
            if stat is not None and Path(full_path).is_file():
                result = await run_in_threadpool(
                    variant, Path(full_path), self.cache, int(query["width"])
                )
                if result:
                    target, version = result
                    response = self.file_response(str(target), target.stat(), scope)
                    response.headers["Content-Type"] = "image/webp"
                    if query.get("v") == version:
                        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                    return response
        response = await super().get_response(path, scope)
        media_type = IMAGE_MEDIA_TYPES.get(PurePosixPath(path).suffix.lower())
        if media_type and response.status_code == 200:
            response.headers["Content-Type"] = media_type
        return response
