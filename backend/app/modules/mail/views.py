"""Mail status and controlled tests to the authenticated administrator's address."""

from fastapi import APIRouter

from app.common.models import MessageResponse
from app.core.dependencies import DbSession, SettingsDependency
from app.modules.auth.dependencies import CurrentAdmin
from app.modules.mail import service
from app.modules.mail.models import MailStatus

router = APIRouter(prefix="/admin/mail", tags=["admin mail"])


@router.get("", response_model=MailStatus)
def get_mail_status(user: CurrentAdmin, settings: SettingsDependency) -> MailStatus:
    return service.get_status(settings=settings, user=user)


@router.post("/test", response_model=MessageResponse)
def send_test_email(
    user: CurrentAdmin, settings: SettingsDependency, db_session: DbSession
) -> MessageResponse:
    service.test_delivery(db_session=db_session, settings=settings, user=user)
    return MessageResponse(
        message="Test email submitted. Check your recovery inbox and spam folder."
    )
