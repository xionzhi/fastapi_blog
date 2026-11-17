"""HTTP adapters for public site information and administrator settings."""

from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession, SettingsDependency
from app.modules.auth.dependencies import get_current_user
from app.modules.site import service
from app.modules.site.models import SiteInput, SiteRead

router = APIRouter(tags=["site"])


@router.get("/site", response_model=SiteRead, response_model_exclude_none=True)
def get_site(db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.get(db_session=db_session, settings=settings)


@router.put(
    "/admin/site",
    response_model=SiteRead,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user)],
)
def update_site(data: SiteInput, db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.update(db_session=db_session, data=data, settings=settings)


@router.get(
    "/admin/site",
    response_model=SiteRead,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user)],
)
def get_admin_site(db_session: DbSession, settings: SettingsDependency) -> SiteRead:
    return service.get(db_session=db_session, settings=settings)
