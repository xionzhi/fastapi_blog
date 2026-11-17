"""Browser caching and text compression without recompressing images or byte ranges."""

import re

from starlette.datastructures import MutableHeaders
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.paths import is_workspace_path

PUBLIC_APIS = ("/api/posts", "/api/tags", "/api/site")
BINARY_SUFFIXES = (
    ".webp",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)


class TextCompressionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=1024, compresslevel=5)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or path.lower().endswith(BINARY_SUFFIXES)
            or b"range" in dict(scope.get("headers", []))
        ):
            await self.app(scope, receive, send)
        else:
            await self.compressed(scope, receive, send)


class ResponseCacheMiddleware:
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")

        async def respond(message: Message) -> None:
            if message["type"] == "http.response.start" and scope.get("method") in {"GET", "HEAD"}:
                headers = MutableHeaders(scope=message)
                if (
                    message["status"] in {200, 206, 304}
                    and not is_workspace_path(path)
                    and not path.startswith(("/api/admin/", "/api/auth/"))
                ):
                    if not self.settings.is_production:
                        headers["Cache-Control"] = "no-cache"
                    elif path.startswith("/assets/") or path.lower().endswith((".woff", ".woff2")):
                        headers["Cache-Control"] = "public, max-age=31536000, immutable"
                    elif path.startswith("/content/images/"):
                        immutable = bool(re.search(r"/[a-f0-9]{32}\.[a-z]+$", path))
                        headers["Cache-Control"] = headers.get("Cache-Control") or (
                            "public, max-age=31536000, immutable"
                            if immutable
                            else "public, max-age=86400, stale-while-revalidate=604800"
                        )
                    elif any(
                        path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_APIS
                    ) or path in {"/rss", "/rss/", "/sitemap.xml", "/robots.txt"}:
                        headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
                    elif path.startswith("/legacy/"):
                        headers["Cache-Control"] = "public, max-age=86400"
                    elif headers.get("content-type", "").startswith("text/html"):
                        headers["Cache-Control"] = "no-cache"
            await send(message)

        await self.app(scope, receive, respond)
