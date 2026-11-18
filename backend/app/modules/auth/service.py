"""Administrator authentication and sessions with mapped persistence."""

import re
import secrets
import time
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.common.database import begin_write
from app.common.exceptions import AuthenticationError, RateLimitError
from app.core.config import Settings
from app.core.security import digest_token, verify_password
from app.modules.auth.models import (
    CurrentUser,
    LoginAttemptOrm,
    PasswordResetOrm,
    SessionOrm,
    UserOrm,
)
from app.modules.auth.rate_limit import consume_limit

DUMMY_PASSWORD_HASH = "scrypt$16384$8$5$00000000000000000000000000000000$" + "0" * 128
LOGIN_WINDOW_SECONDS = 900
MAX_LOGIN_ATTEMPTS = 10


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    username: str
    token: str
    duration: int


def get_session_user(*, db_session: Session, token: str) -> CurrentUser:
    if not re.fullmatch(r"[A-Za-z0-9_-]{64}", token):
        raise AuthenticationError()
    user = db_session.scalar(
        select(UserOrm)
        .join(SessionOrm, SessionOrm.user_id == UserOrm.id)
        .where(
            SessionOrm.token_hash == digest_token(token), SessionOrm.expires_at > int(time.time())
        )
    )
    if user is None:
        raise AuthenticationError()
    return CurrentUser.model_validate(user)


def sign_in(
    *, db_session: Session, settings: Settings, username: str, password: str, client_ip: str
) -> AuthenticatedSession:
    timestamp = int(time.time())
    key = "login:" + digest_token(client_ip)
    begin_write(db_session)
    db_session.execute(delete(SessionOrm).where(SessionOrm.expires_at <= timestamp))
    db_session.execute(delete(LoginAttemptOrm).where(LoginAttemptOrm.reset_at <= timestamp))
    allowed = consume_limit(
        db_session, key, timestamp, maximum=MAX_LOGIN_ATTEMPTS, window=LOGIN_WINDOW_SECONDS
    )
    db_session.commit()
    if not allowed:
        raise RateLimitError("Too many sign-in attempts. Try again in 15 minutes.")
    user = db_session.scalar(select(UserOrm).where(UserOrm.username == username))
    user_id = user.id if user else None
    encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
    db_session.commit()
    # Password work runs outside SQLite write locks; attempts have already been persisted.
    valid = verify_password(password, encoded)
    if user_id is None or not valid:
        raise AuthenticationError("Incorrect username or password")
    begin_write(db_session)
    user = db_session.get(UserOrm, user_id, populate_existing=True)
    if user is None or user.password_hash != encoded:
        raise AuthenticationError("Your credentials changed. Please sign in again.")
    db_session.execute(delete(LoginAttemptOrm).where(LoginAttemptOrm.key == key))
    token = secrets.token_urlsafe(48)
    duration = settings.session_hours * 3600
    db_session.add(
        SessionOrm(token_hash=digest_token(token), user_id=user.id, expires_at=timestamp + duration)
    )
    return AuthenticatedSession(username=user.username, token=token, duration=duration)


def sign_out(*, db_session: Session, token: str) -> None:
    db_session.execute(delete(SessionOrm).where(SessionOrm.token_hash == digest_token(token)))


def purge_expired(*, session: Session) -> None:
    timestamp = int(time.time())
    session.execute(delete(SessionOrm).where(SessionOrm.expires_at <= timestamp))
    session.execute(delete(PasswordResetOrm).where(PasswordResetOrm.expires_at <= timestamp))
    session.execute(delete(LoginAttemptOrm).where(LoginAttemptOrm.reset_at <= timestamp))
