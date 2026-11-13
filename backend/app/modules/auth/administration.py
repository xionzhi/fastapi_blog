"""Trusted server-console operations using the same mapped administrator model."""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import ConflictError, NotFoundError
from app.common.time import utc_now
from app.core.security import hash_password
from app.modules.auth.models import CurrentUser, PasswordResetOrm, SessionOrm, UserOrm
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
