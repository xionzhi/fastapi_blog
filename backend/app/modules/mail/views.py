"""Mail status and controlled tests to the authenticated administrator's address."""

from fastapi import APIRouter, BackgroundTasks, Request

from app.common.models import MessageResponse
from app.core.dependencies import DbSession, SettingsDependency
from app.core.security import session_cookie_name
from app.modules.auth import administration
from app.modules.auth.dependencies import CurrentAdmin
from app.modules.mail import service
from app.modules.mail.models import MailStatus, RecoveryEmailInput

router = APIRouter(prefix="/admin/mail", tags=["admin mail"])


@router.get("", response_model=MailStatus)
def get_mail_status(user: CurrentAdmin, settings: SettingsDependency) -> MailStatus:
    return service.get_status(settings=settings, user=user)


@router.put("", response_model=MailStatus)
def update_recovery_email(
    data: RecoveryEmailInput,
    request: Request,
    user: CurrentAdmin,
    settings: SettingsDependency,
    db_session: DbSession,
    background_tasks: BackgroundTasks,
) -> MailStatus:
    updated, previous = administration.update_recovery_email(
        db_session=db_session,
        user=user,
        data=data,
        session_token=request.cookies[session_cookie_name(settings)],
    )
    if previous:
        background_tasks.add_task(service.recovery_email_changed, settings, previous, user.username)
    return service.get_status(settings=settings, user=updated)


@router.post("/test", response_model=MessageResponse)
def send_test_email(
    user: CurrentAdmin, settings: SettingsDependency, db_session: DbSession
) -> MessageResponse:
    service.test_delivery(db_session=db_session, settings=settings, user=user)
    return MessageResponse(
        message="Test email submitted. Check your recovery inbox and spam folder."
    )
