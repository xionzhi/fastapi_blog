"""One-time password recovery with explicit transaction and delivery boundaries."""

import secrets
import time
from dataclasses import dataclass

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.common.database import begin_write
from app.common.exceptions import ApplicationError, RateLimitError
from app.core.config import Settings
from app.core.security import digest_token, hash_password
from app.modules.auth.models import (
    CurrentUser,
    LoginAttemptOrm,
    PasswordResetOrm,
    SessionOrm,
    UserOrm,
)
from app.modules.auth.rate_limit import consume_limit

RESET_TTL_SECONDS = 900
RESET_RESPONSE_MESSAGE = (
    "If this account has a recovery email, you will receive a reset link. "
    "Check your inbox and spam folder."
)


@dataclass(frozen=True, slots=True)
class ResetDelivery:
    recipient: str
    username: str
    token: str


def require_enabled(settings: Settings) -> None:
    if not settings.mail_enabled:
        raise ApplicationError(
            "Email recovery is not enabled. Contact the blog administrator.",
            code="mail.disabled",
            status_code=503,
        )


def request_reset(
    *,
    db_session: Session,
    settings: Settings,
    identifier: str,
    client_ip: str,
) -> ResetDelivery | None:
    require_enabled(settings)
    timestamp = int(time.time())
    identifier = identifier.strip()
    begin_write(db_session)
    db_session.execute(delete(PasswordResetOrm).where(PasswordResetOrm.expires_at <= timestamp))
    db_session.execute(delete(LoginAttemptOrm).where(LoginAttemptOrm.reset_at <= timestamp))
    if not consume_limit(
        db_session, "reset-ip:" + digest_token(client_ip), timestamp, maximum=5, window=900
    ):
        raise RateLimitError("Too many requests. Please try again in 15 minutes.")

    user = db_session.scalar(
        select(UserOrm).where(
            or_(UserOrm.username == identifier, func.lower(UserOrm.email) == identifier.lower())
        )
    )
    delivery = None
    if (
        user
        and user.email
        and consume_limit(
            db_session, "reset-user:" + str(user.id), timestamp, maximum=3, window=3600
        )
    ):
        token = secrets.token_urlsafe(48)
        db_session.add(
            PasswordResetOrm(
                token_hash=digest_token(token),
                user_id=user.id,
                expires_at=timestamp + RESET_TTL_SECONDS,
                created_at=timestamp,
            )
        )
        delivery = ResetDelivery(recipient=user.email, username=user.username, token=token)
    # The background mail task must never run with an uncommitted token or held write lock.
    db_session.commit()
    return delivery


def get_token_user(*, db_session: Session, token: str) -> CurrentUser:
    record = db_session.scalar(
        select(UserOrm)
        .join(PasswordResetOrm, PasswordResetOrm.user_id == UserOrm.id)
        .where(
            PasswordResetOrm.token_hash == digest_token(token),
            PasswordResetOrm.expires_at > int(time.time()),
        )
    )
    if record is None:
        raise ApplicationError(
            "This reset link is invalid or expired. Please request a new one.",
            code="auth.invalid_reset_token",
        )
    return CurrentUser.model_validate(record)


def reset_password(
    *, db_session: Session, settings: Settings, token: str, password: str
) -> CurrentUser:
    require_enabled(settings)
    begin_write(db_session)
    user = get_token_user(db_session=db_session, token=token)
    record = db_session.get(UserOrm, user.id)
    if record is None:
        raise ApplicationError("Administrator no longer exists", code="auth.user_missing")
    record.password_hash = hash_password(password)
    db_session.execute(delete(SessionOrm).where(SessionOrm.user_id == user.id))
    db_session.execute(delete(PasswordResetOrm).where(PasswordResetOrm.user_id == user.id))
    db_session.commit()
    return user
