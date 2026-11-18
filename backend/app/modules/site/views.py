"""HTTP adapters for public site information and administrator settings."""

from fastapi import APIRouter

from app.core.dependencies import DbSession, SettingsDependency
from app.modules.site import service
from app.modules.site.models import SiteInput, SiteRead

router = APIRouter(tags=["site"])
admin_router = APIRouter(prefix="/site", tags=["admin site"])


@router.get("/site", response_model=SiteRead, response_model_exclude_none=True)
def get_site(db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.get(db_session=db_session, settings=settings)


@admin_router.put(
    "",
    response_model=SiteRead,
    response_model_exclude_none=True,
)
def update_site(data: SiteInput, db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.update(db_session=db_session, data=data, settings=settings)


@admin_router.get(
    "",
    response_model=SiteRead,
    response_model_exclude_none=True,
)
def get_admin_site(db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.get(db_session=db_session, settings=settings)
