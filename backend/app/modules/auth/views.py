"""Session cookies and password recovery HTTP endpoints."""

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.common.models import MessageResponse, SuccessResponse
from app.core.dependencies import DbSession, SettingsDependency
from app.core.security import check_origin, csrf_token, session_cookie_name
from app.modules.auth import recovery, service
from app.modules.auth.dependencies import CurrentAdmin
from app.modules.auth.models import (
    ForgotPassword,
    Login,
    NewPassword,
    RecoveryStatus,
    ResetToken,
    SessionResponse,
    ValidTokenResponse,
)
from app.modules.mail import service as mail_service

router = APIRouter(tags=["authentication"])


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/admin/login", response_model=SessionResponse)
def sign_in(
    data: Login,
    request: Request,
    response: Response,
    settings: SettingsDependency,
    db_session: DbSession,
) -> SessionResponse:
    check_origin(request=request, settings=settings)
    session = service.sign_in(
        db_session=db_session,
        settings=settings,
        username=data.username,
        password=data.password,
        client_ip=client_ip(request),
    )
    response.set_cookie(
        session_cookie_name(settings),
        session.token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        max_age=session.duration,
        path="/",
    )
    return SessionResponse(username=session.username, csrf_token=csrf_token(session.token))


@router.get("/admin/me", response_model=SessionResponse)
def get_session(
    request: Request, user: CurrentAdmin, settings: SettingsDependency
) -> SessionResponse:
    return SessionResponse(
        username=user.username,
        csrf_token=csrf_token(request.cookies[session_cookie_name(settings)]),
    )


@router.post("/admin/logout", response_model=SuccessResponse)
def sign_out(
    request: Request,
    response: Response,
    user: CurrentAdmin,
    settings: SettingsDependency,
    db_session: DbSession,
) -> SuccessResponse:
    service.sign_out(db_session=db_session, token=request.cookies[session_cookie_name(settings)])
    response.delete_cookie(
        session_cookie_name(settings),
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )
    return SuccessResponse()


@router.get("/auth/recovery", response_model=RecoveryStatus)
def get_recovery_status(settings: SettingsDependency) -> RecoveryStatus:
    return RecoveryStatus(enabled=settings.mail_enabled)


@router.post("/auth/forgot-password", response_model=MessageResponse)
def request_password_reset(
    data: ForgotPassword,
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDependency,
    db_session: DbSession,
) -> MessageResponse:
    check_origin(request=request, settings=settings)
    delivery = recovery.request_reset(
        db_session=db_session,
        settings=settings,
        identifier=data.identifier,
        client_ip=client_ip(request),
    )
    if delivery:
        background_tasks.add_task(
            mail_service.send_reset,
            settings,
            delivery.recipient,
            delivery.username,
            delivery.token,
        )
    return MessageResponse(message=recovery.RESET_RESPONSE_MESSAGE)


@router.post("/auth/reset-password/check", response_model=ValidTokenResponse)
def check_reset_token(
    data: ResetToken,
    request: Request,
    settings: SettingsDependency,
    db_session: DbSession,
) -> ValidTokenResponse:
    check_origin(request=request, settings=settings)
    recovery.require_enabled(settings)
    recovery.get_token_user(db_session=db_session, token=data.token)
    return ValidTokenResponse()


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(
    data: NewPassword,
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDependency,
    db_session: DbSession,
) -> MessageResponse:
    check_origin(request=request, settings=settings)
    user = recovery.reset_password(
        db_session=db_session, settings=settings, token=data.token, password=data.password
    )
    background_tasks.add_task(mail_service.password_changed, settings, user.email, user.username)
    return MessageResponse(
        message="Your password has been reset and previous sessions have been signed out. "
        "Sign in with your new password."
    )
