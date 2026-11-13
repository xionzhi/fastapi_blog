"""Validated site configuration and public content statistics."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.database import read_settings
from app.common.time import utc_now
from app.modules.post.models import PostOrm
from app.modules.site.models import SiteInput, SiteRead, SiteSettingOrm, SiteStats
from app.modules.tag.service import list_tags


def get(*, db_session: Session, include_stats: bool = True) -> SiteRead:
    data = read_settings(db_session)
    if include_stats:
        count = (
            db_session.scalar(
                select(func.count())
                .select_from(PostOrm)
                .where(
                    PostOrm.status == "published",
                    PostOrm.type == "post",
                    PostOrm.published_at <= utc_now(),
                )
            )
            or 0
        )
        data["stats"] = SiteStats(posts=count, tags=len(list_tags(db_session)))
    return SiteRead.model_validate(data)


def update(*, db_session: Session, data: SiteInput) -> SiteRead:
    for key, value in data.model_dump().items():
        setting = db_session.get(SiteSettingOrm, key)
        if setting:
            setting.value = value
        else:
            db_session.add(SiteSettingOrm(key=key, value=value))
    db_session.flush()
    return get(db_session=db_session, include_stats=False)
