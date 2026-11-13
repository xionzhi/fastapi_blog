from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.common.database import connect
from app.common.maintenance import run_maintenance
from app.common.time import utc_now
from app.modules.analytics.models import DailyTrafficOrm, DailyVisitorOrm, PageTrafficOrm


def payload(path="/", visitor=None, event=None):
    return {"path": path, "visitor_id": str(visitor or uuid4()), "event_id": str(event or uuid4())}


def test_anonymous_counts_are_deduplicated_and_protected(admin, post_data):
    admin.post("/api/admin/posts", json=post_data)
    visitor = TestClient(admin.app)
    identity = uuid4()
    first = payload(visitor=identity)
    try:
        assert visitor.get("/api/admin/analytics").status_code == 401
        assert visitor.post("/api/analytics/events", json=first).status_code == 204
        assert visitor.post("/api/analytics/events", json=first).status_code == 204
        visitor.post("/api/analytics/events", json=payload("/python-notes/", identity))
        visitor.post("/api/analytics/events", json=payload())
    finally:
        visitor.close()
    response = admin.get("/api/admin/analytics?days=7")
    assert response.status_code == 200, response.text
    overview = response.json()
    assert overview["total_views"] == 3 and overview["today_visitors"] == 2
    assert len(overview["series"]) == 7
    assert len(admin.get("/api/admin/analytics?days=30").json()["series"]) == 30
    assert len(admin.get("/api/admin/analytics?days=90").json()["series"]) == 90
    assert overview["popular_pages"][0]["path"] == "/"
    with connect(admin.app.state.settings) as session:
        identifiers = session.scalars(select(DailyVisitorOrm.visitor_hash)).all()
        assert len(identifiers) == 2 and str(identity) not in identifiers


def test_bots_privacy_signals_prefetch_and_administrators_are_excluded(admin):
    assert admin.post("/api/analytics/events", json=payload()).status_code == 204
    visitor = TestClient(admin.app)
    try:
        for headers in (
            {"User-Agent": "Googlebot"},
            {"User-Agent": "curl/8"},
            {"DNT": "1"},
            {"Sec-GPC": "1"},
            {"Sec-Purpose": "prefetch"},
        ):
            assert (
                visitor.post("/api/analytics/events", json=payload(), headers=headers).status_code
                == 204
            )
    finally:
        visitor.close()
    assert admin.get("/api/admin/analytics").json()["total_views"] == 0


def test_invalid_private_and_missing_pages_are_not_recorded(admin):
    visitor = TestClient(admin.app)
    try:
        for path in (
            "/workspace/login/",
            "/api/health/",
            "/not-a-post/",
            "/tag/missing/",
            "/page/99999/",
        ):
            assert visitor.post("/api/analytics/events", json=payload(path)).status_code == 204
        for path in ("https://attacker.example/", "/?password=private", "/#private", "/../secret"):
            assert visitor.post("/api/analytics/events", json=payload(path)).status_code == 422
        assert (
            visitor.post(
                "/api/analytics/events",
                json=payload(),
                headers={"Origin": "https://attacker.example"},
            ).status_code
            == 403
        )
    finally:
        visitor.close()
    assert admin.get("/api/admin/analytics").json()["total_views"] == 0


def test_collection_quota_bounds_new_visitor_rows(admin):
    settings = admin.app.state.settings
    day = utc_now().date()
    with connect(settings) as session:
        session.add(DailyTrafficOrm(day=day, views=settings.analytics_max_daily_views, visitors=1))
    visitor = TestClient(admin.app)
    try:
        assert visitor.post("/api/analytics/events", json=payload()).status_code == 204
    finally:
        visitor.close()
    overview = admin.get("/api/admin/analytics").json()
    assert overview["daily_limit_reached"]
    assert overview["total_views"] == settings.analytics_max_daily_views
    with connect(settings) as session:
        assert session.scalar(select(func.count()).select_from(DailyVisitorOrm)) == 0


def test_retention_removes_old_aggregates_and_yesterdays_identifiers(client):
    today = utc_now().date()
    old = today - timedelta(days=100)
    yesterday = today - timedelta(days=1)
    with connect(client.app.state.settings) as session:
        session.add_all(
            [
                DailyTrafficOrm(day=old, views=1, visitors=1),
                DailyTrafficOrm(day=yesterday, views=1, visitors=1),
            ]
        )
        session.flush()
        for day in (old, yesterday):
            session.add(PageTrafficOrm(day=day, path="/", post_id=None, views=1))
            session.add(DailyVisitorOrm(day=day, visitor_hash="a" * 64, last_event_id=uuid4().hex))
    run_maintenance(client.app.state.database)
    with connect(client.app.state.settings) as session:
        assert session.get(DailyTrafficOrm, old) is None
        assert session.get(DailyTrafficOrm, yesterday) is not None
        assert session.scalar(select(func.count()).select_from(DailyVisitorOrm)) == 0
        assert session.scalar(select(func.count()).select_from(PageTrafficOrm)) == 1


def test_collection_can_be_disabled(admin):
    admin.app.state.settings = admin.app.state.settings.model_copy(
        update={"analytics_enabled": False}
    )
    visitor = TestClient(admin.app)
    try:
        visitor.post("/api/analytics/events", json=payload())
    finally:
        visitor.close()
    overview = admin.get("/api/admin/analytics").json()
    assert not overview["enabled"] and overview["total_views"] == 0
