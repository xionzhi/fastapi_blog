"""HTTP security policy, bounded bodies, and request correlation."""

import logging
import uuid

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.paths import WORKSPACE_PATH, is_workspace_path

logger = logging.getLogger("blog.http")


def content_security_policy(*, cloudflare: bool = False) -> str:
    scripts = "'self'"
    connections = "'self'"
    if cloudflare:
        scripts += " https://static.cloudflareinsights.com"
        connections += " https://cloudflareinsights.com"
    return (
        "default-src 'self'; img-src 'self' https: http: data:; "
        f"style-src 'self' 'unsafe-inline'; script-src {scripts}; connect-src {connections}; "
        "font-src 'self'; media-src 'self' https:; frame-src 'none'; object-src 'none'; "
        "base-uri 'self'; form-action 'self'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.public_csp = content_security_policy(cloudflare=settings.cloudflare_analytics_enabled)
        self.workspace_csp = content_security_policy()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "X-Request-ID": request.state.request_id,
            }
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if self.settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith(("/api/admin", "/api/auth")) or is_workspace_path(
            request.url.path
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        if request.url.path == f"{WORKSPACE_PATH}/reset-password":
            response.headers["Referrer-Policy"] = "no-referrer"
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = (
                self.workspace_csp if is_workspace_path(request.url.path) else self.public_csp
            )
        return response


class RequestSizeLimitMiddleware:
    """Enforce the configured limit even when Content-Length is missing or incorrect."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        path = scope.get("path", "")
        limit = self.max_bytes
        if path == "/api/admin/login" or path.startswith("/api/auth/"):
            limit = min(limit, 8192)
        elif path == "/api/analytics/events":
            limit = min(limit, 2048)
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError("negative length")
        except ValueError:
            await Response("Invalid Content-Length", status_code=400)(scope, receive, send)
            return
        if length > limit:
            await Response("Request too large", status_code=413)(scope, receive, send)
            return
        consumed = 0

        async def bounded_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > limit:
                    raise HTTPException(status_code=413, detail="Request too large")
            return message

        await self.app(scope, bounded_receive, send)
