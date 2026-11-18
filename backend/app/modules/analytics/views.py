"""Anonymous collection and authenticated traffic reports; never request logging."""

import re

from fastapi import APIRouter, Query, Request, Response

from app.common.exceptions import AuthenticationError
from app.core.dependencies import DbSession, SettingsDependency
from app.core.security import check_origin, session_cookie_name
from app.modules.analytics import service
from app.modules.analytics.models import PageViewInput, TrafficOverview
from app.modules.auth.service import get_session_user

router = APIRouter(tags=["analytics"])
admin_router = APIRouter(prefix="/analytics", tags=["admin analytics"])
BOT = re.compile(
    r"bot|spider|crawl|slurp|headless|curl|wget|python|httpclient|scrapy|scanner|monitor|uptime|preview",
    re.IGNORECASE,
)


@router.post("/analytics/events", status_code=204, response_class=Response)
def collect_page_view(
    data: PageViewInput, request: Request, settings: SettingsDependency, db_session: DbSession
) -> Response:
    check_origin(request=request, settings=settings)
    headers = request.headers
    if (
        not settings.analytics_enabled
        or headers.get("dnt") == "1"
        or headers.get("sec-gpc") == "1"
        or "prefetch" in (headers.get("purpose", "") + headers.get("sec-purpose", "")).lower()
        or not headers.get("user-agent")
        or BOT.search(headers.get("user-agent", ""))
    ):
        return Response(status_code=204)
    if token := request.cookies.get(session_cookie_name(settings)):
        try:
            get_session_user(db_session=db_session, token=token)
        except AuthenticationError:
            pass
        else:
            return Response(status_code=204)
    service.record_view(session=db_session, settings=settings, data=data)
    return Response(status_code=204)


@admin_router.get("", response_model=TrafficOverview)
def get_traffic_overview(
    settings: SettingsDependency,
    db_session: DbSession,
    days: int = Query(default=30, ge=7, le=90),
) -> TrafficOverview:
    return service.get_overview(session=db_session, settings=settings, days=days)
