"""Administrator maintenance and password-confirmed recovery address changes."""

import time

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.database import begin_write
from app.common.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from app.common.time import utc_now
from app.core.security import digest_token, hash_password, verify_password
from app.modules.auth.models import (
    CurrentUser,
    LoginAttemptOrm,
    PasswordResetOrm,
    SessionOrm,
    UserOrm,
)
from app.modules.auth.rate_limit import consume_limit
from app.modules.mail.models import RecoveryEmailInput
from app.modules.mail.validation import validate_email_address


def save_administrator(
    *,
    db_session: Session,
    username: str,
    password: str,
    email: str = "",
    reset_password: bool = False,
) -> CurrentUser | None:
    if not username.strip() or len(username) > 80:
        raise ValueError("Username must contain between 1 and 80 characters")
    email = validate_email_address(email) if email else ""
    encoded = hash_password(password)
    user = db_session.scalar(select(UserOrm).where(UserOrm.username == username))
    previous = None
    if user:
        if not reset_password:
            raise ConflictError("Admin already exists; use --reset-password to change the password")
        previous = CurrentUser.model_validate(user)
        user.password_hash = encoded
        user.email = email or user.email
        db_session.execute(delete(SessionOrm).where(SessionOrm.user_id == user.id))
        db_session.execute(delete(PasswordResetOrm).where(PasswordResetOrm.user_id == user.id))
    else:
        db_session.add(
            UserOrm(username=username, password_hash=encoded, created_at=utc_now(), email=email)
        )
    try:
        db_session.flush()
    except IntegrityError as error:
        raise ConflictError(
            "That recovery email is already bound to another administrator"
        ) from error
    return previous


def get_administrator(*, db_session: Session, username: str) -> CurrentUser:
    user = db_session.scalar(select(UserOrm).where(UserOrm.username == username))
    if user is None:
        raise NotFoundError("Administrator does not exist")
    return CurrentUser.model_validate(user)


def bind_email(*, db_session: Session, username: str, email: str) -> None:
    user = get_administrator(db_session=db_session, username=username)
    record = db_session.get(UserOrm, user.id)
    if record is None:
        raise NotFoundError("Administrator does not exist")
    record.email = validate_email_address(email)
    db_session.execute(delete(PasswordResetOrm).where(PasswordResetOrm.user_id == user.id))
    try:
        db_session.flush()
    except IntegrityError as error:
        raise ConflictError(
            "That recovery email is already bound to another administrator"
        ) from error


def update_recovery_email(
    *, db_session: Session, user: CurrentUser, session_token: str, data: RecoveryEmailInput
) -> tuple[CurrentUser, str]:
    timestamp = int(time.time())
    key = "email-change:" + str(user.id)
    begin_write(db_session)
    allowed = consume_limit(db_session, key, timestamp, maximum=5, window=900)
    record = db_session.get(UserOrm, user.id, populate_existing=True)
    encoded = record.password_hash if record else ""
    # Keep failed password attempts even when the subsequent operation rolls back.
    db_session.commit()
    if not allowed:
        raise RateLimitError("Too many email change attempts. Try again in 15 minutes.")
    if not encoded:
        raise AuthenticationError()
    if not verify_password(data.current_password.get_secret_value(), encoded):
        raise ApplicationError(
            "Incorrect current password", code="auth.invalid_password", status_code=403
        )

    # Verify outside the write lock, then recheck credentials and session under the lock.
    begin_write(db_session)
    record = db_session.get(UserOrm, user.id, populate_existing=True)
    token_hash = digest_token(session_token)
    current_session = db_session.get(SessionOrm, token_hash, populate_existing=True)
    if (
        record is None
        or record.password_hash != encoded
        or current_session is None
        or current_session.user_id != user.id
        or current_session.expires_at <= int(time.time())
    ):
        raise AuthenticationError("Your credentials changed. Please sign in again.")
    previous = ""
    if record.email.casefold() != data.email.casefold():
        if record.email != data.previous_email:
            raise ConflictError(
                "Your recovery email changed. Reload this page and review it before saving.",
                code="mail.email_changed",
            )
        previous = record.email
        bind_email(db_session=db_session, username=user.username, email=data.email)
        db_session.execute(
            delete(SessionOrm).where(
                SessionOrm.user_id == user.id, SessionOrm.token_hash != token_hash
            )
        )
    db_session.execute(delete(LoginAttemptOrm).where(LoginAttemptOrm.key == key))
    return CurrentUser.model_validate(record), previous
