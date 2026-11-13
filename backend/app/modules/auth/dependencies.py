"""Authentication adapters for protected HTTP routes."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.dependencies import DbSession, SettingsDependency
from app.core.security import UNSAFE_METHODS, check_csrf, session_cookie_name
from app.modules.auth import service
from app.modules.auth.models import CurrentUser


def get_current_user(
    request: Request,
    db_session: DbSession,
    settings: SettingsDependency,
) -> CurrentUser:
    token = request.cookies.get(session_cookie_name(settings), "")
    user = service.get_session_user(db_session=db_session, token=token)
    if request.method in UNSAFE_METHODS:
        check_csrf(request=request, session_token=token, settings=settings)
    return user


CurrentAdmin = Annotated[CurrentUser, Depends(get_current_user)]
