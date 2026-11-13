"""Application composition and lifecycle. No route logic or import-time database writes."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import api_router
from app.common.database import Database
from app.common.maintenance import periodic_maintenance, run_maintenance
from app.core.cache import ResponseCacheMiddleware, TextCompressionMiddleware
from app.core.config import Settings
from app.core.exception_handlers import register_exception_handlers
from app.core.ingress import IngressGuardMiddleware
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.modules.media.static import ImageStaticFiles
from app.modules.publishing.views import router as publishing_router


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = cast(Database, app.state.database)
    database.initialize()
    await asyncio.to_thread(run_maintenance, database)
    maintenance = asyncio.create_task(periodic_maintenance(database))
    try:
        yield
    finally:
        maintenance.cancel()
        with suppress(asyncio.CancelledError):
            await maintenance
        database.dispose()


def build_application(*, settings: Settings) -> FastAPI:
    """Assemble an isolated app from explicitly supplied, validated settings."""
    app = FastAPI(
        title="Xionzhi Blog API",
        version="1.0.0",
        lifespan=application_lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.database = Database(settings)
    register_exception_handlers(app)
    app.add_middleware(TextCompressionMiddleware)
    app.add_middleware(ResponseCacheMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts, www_redirect=False
    )
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(IngressGuardMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxy_networks)
    app.include_router(api_router)
    app.mount(
        "/content/images",
        ImageStaticFiles(directory=settings.images, check_dir=False),
        name="images",
    )
    for directory in ("assets", "legacy"):
        path = settings.frontend_dir / directory
        if path.is_dir():
            app.mount(f"/{directory}", StaticFiles(directory=path), name=directory)
    app.include_router(publishing_router)
    return app
