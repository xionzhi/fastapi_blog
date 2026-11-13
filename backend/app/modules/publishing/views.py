"""Public documents and the Vue entry document; registered after all API routes."""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse

from app.core.dependencies import SettingsDependency
from app.core.paths import WORKSPACE_PATH
from app.modules.publishing import service

router = APIRouter(tags=["publishing"])


@router.get("/rss", include_in_schema=False)
@router.get("/rss/", include_in_schema=False)
def get_rss(settings: SettingsDependency) -> Response:
    return service.rss(config=settings)


@router.get("/sitemap.xml", include_in_schema=False)
def get_sitemap(settings: SettingsDependency) -> Response:
    return service.sitemap(config=settings)


@router.get("/robots.txt", include_in_schema=False)
def get_robots(settings: SettingsDependency) -> Response:
    return Response(
        f"User-agent: *\nAllow: /\nDisallow: {WORKSPACE_PATH}\nDisallow: /api/\n"
        f"Sitemap: {settings.site_url}/sitemap.xml\n",
        media_type="text/plain",
    )


@router.head("/{path:path}", include_in_schema=False)
@router.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def get_frontend_document(path: str, settings: SettingsDependency) -> Response:
    normalized = path.strip("/")
    if normalized == "admin" or normalized.startswith("admin/"):
        raise HTTPException(status_code=404)
    if path.startswith(("api/", "assets/", "content/", "legacy/")):
        raise HTTPException(status_code=404)
    if path == "favicon.ico" and (settings.frontend_dir / "favicon.ico").exists():
        return FileResponse(settings.frontend_dir / "favicon.ico")
    index = settings.frontend_dir / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>The site frontend is not available.</h1>", status_code=503)
    return service.seo_page(settings, index, path)
