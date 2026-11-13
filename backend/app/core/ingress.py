"""Reject scanner probes and bursts before routing, body parsing, or database access."""

from pathlib import PurePosixPath

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.rate_limit import WindowLimiter


class IngressGuardMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.limiter = WindowLimiter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        status = 0
        if len(path) > 2048 or len(scope.get("query_string", b"")) > 2048:
            status = 414
        elif any(
            part.startswith(".") for part in PurePosixPath(path).parts
        ) or path.lower().endswith((".php", ".asp", ".aspx", ".jsp")):
            status = 404
        if status:
            await JSONResponse(
                {"detail": "Not found", "error_code": "request.rejected"}, status_code=status
            )(scope, receive, send)
            return
        client = scope.get("client")
        address = client[0] if client else "unknown"
        if (
            path == "/api/admin/login"
            or path.startswith("/api/auth/")
            and scope["method"] == "POST"
        ):
            category, maximum = "auth", 15
        elif path == "/api/analytics/events":
            category, maximum = "analytics", 60
        elif path.startswith("/api/"):
            category, maximum = "api", 120
        else:
            category, maximum = "public", 300
        allowed = self.limiter.allow(f"{category}:{address}", maximum=maximum, seconds=60)
        if category == "auth":
            allowed = allowed and self.limiter.allow("global:auth", maximum=30, seconds=60)
        if not allowed:
            await JSONResponse(
                {
                    "detail": "Too many requests. Please try again shortly.",
                    "error_code": "request.rate_limited",
                },
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)
