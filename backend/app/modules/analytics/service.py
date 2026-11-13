"""Validated page counts, bounded retention, and administrator-only summaries."""

import hashlib
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.common.database import begin_write
from app.common.time import utc_now
from app.core.config import Settings
from app.modules.analytics.models import (
    DailyMetric,
    DailyTrafficOrm,
    DailyVisitorOrm,
    PageTrafficOrm,
    PageViewInput,
    PopularPage,
    TrafficOverview,
)
from app.modules.post.models import PostOrm, PostTagOrm
from app.modules.post.service import public_predicate
from app.modules.site.models import SiteSettingOrm
from app.modules.tag.models import TagOrm


def resolve_page(session: Session, path: str) -> tuple[bool, str | None]:
    parts = path.strip("/").split("/") if path != "/" else []
    if not parts or parts in (["archive"], ["tags"]):
        return True, None
    if len(parts) == 1:
        post_id = session.scalar(
            select(PostOrm.id).where(PostOrm.slug == parts[0], public_predicate())
        )
        return post_id is not None, post_id
    query = (
        select(func.count()).select_from(PostOrm).where(PostOrm.type == "post", public_predicate())
    )
    if parts[0] == "tag" and len(parts) in (2, 4):
        query = query.join(PostTagOrm).join(TagOrm).where(TagOrm.slug == parts[1])
        remaining = parts[2:]
    elif parts[0] == "author" and len(parts) in (2, 4):
        query = query.where(PostOrm.author_slug == parts[1])
        remaining = parts[2:]
    elif parts[0] == "page" and len(parts) == 2:
        remaining = parts
    else:
        return False, None
    count = session.scalar(query) or 0
    if not count and parts[0] != "page":
        return False, None
    if remaining:
        if len(remaining) != 2 or remaining[0] != "page" or not remaining[1].isdigit():
            return False, None
        page_size = session.get(SiteSettingOrm, "posts_per_page")
        maximum = (
            max(1, (count + int(page_size.value) - 1) // int(page_size.value)) if page_size else 1
        )
        if not 1 <= int(remaining[1]) <= maximum:
            return False, None
    return True, None


def record_view(*, session: Session, settings: Settings, data: PageViewInput) -> bool:
    accepted, post_id = resolve_page(session, data.path)
    if not accepted:
        return False
    day = utc_now().date()
    visitor_hash = hashlib.sha256(f"{day}:{data.visitor_id.hex}".encode()).hexdigest()
    begin_write(session)
    daily = session.get(DailyTrafficOrm, day)
    if daily is None:
        daily = DailyTrafficOrm(day=day, views=0, visitors=0)
        session.add(daily)
        session.flush()
    if daily.views >= settings.analytics_max_daily_views:
        return False
    visitor = session.get(DailyVisitorOrm, (day, visitor_hash))
    if visitor and visitor.last_event_id == data.event_id.hex:
        return False
    if visitor is None:
        session.add(
            DailyVisitorOrm(day=day, visitor_hash=visitor_hash, last_event_id=data.event_id.hex)
        )
        daily.visitors += 1
    else:
        visitor.last_event_id = data.event_id.hex
    daily.views += 1
    page = session.get(PageTrafficOrm, (day, data.path))
    if page is None:
        session.add(PageTrafficOrm(day=day, path=data.path, post_id=post_id, views=1))
    else:
        page.views += 1
    return True


def purge_expired(*, session: Session, settings: Settings) -> None:
    day = utc_now().date()
    session.execute(delete(DailyVisitorOrm).where(DailyVisitorOrm.day < day))
    cutoff = day - timedelta(days=settings.analytics_retention_days - 1)
    session.execute(delete(DailyTrafficOrm).where(DailyTrafficOrm.day < cutoff))


def get_overview(*, session: Session, settings: Settings, days: int) -> TrafficOverview:
    today = utc_now().date()
    start = today - timedelta(days=days - 1)
    records = {
        row.day: row
        for row in session.scalars(
            select(DailyTrafficOrm).where(
                DailyTrafficOrm.day >= start, DailyTrafficOrm.day <= today
            )
        )
    }
    series = [
        DailyMetric(day=day, views=records[day].views, visitors=records[day].visitors)
        if day in records
        else DailyMetric(day=day)
        for day in (start + timedelta(days=index) for index in range(days))
    ]
    totals = func.sum(PageTrafficOrm.views).label("views")
    popular = session.execute(
        select(PageTrafficOrm.path, PostOrm.title, totals)
        .outerjoin(PostOrm, PostOrm.id == PageTrafficOrm.post_id)
        .where(PageTrafficOrm.day >= start, PageTrafficOrm.day <= today)
        .group_by(PageTrafficOrm.path, PostOrm.title)
        .order_by(totals.desc(), PageTrafficOrm.path)
        .limit(10)
    ).all()
    titles = {"/": "Home", "/archive/": "Archive", "/tags/": "Tags"}
    return TrafficOverview(
        enabled=settings.analytics_enabled,
        days=days,
        total_views=sum(row.views for row in series),
        average_daily_visitors=round(sum(row.visitors for row in series) / days, 1),
        today_views=series[-1].views,
        today_visitors=series[-1].visitors,
        daily_limit_reached=series[-1].views >= settings.analytics_max_daily_views,
        retention_days=settings.analytics_retention_days,
        series=series,
        popular_pages=[
            PopularPage(path=path, title=title or titles.get(path, path), views=views)
            for path, title, views in popular
        ],
    )
