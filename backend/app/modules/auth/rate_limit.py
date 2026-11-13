"""Persistent limits; callers own the write transaction."""

from sqlalchemy.orm import Session

from app.modules.auth.models import LoginAttemptOrm


def consume_limit(
    db_session: Session, key: str, timestamp: int, *, maximum: int, window: int
) -> bool:
    record = db_session.get(LoginAttemptOrm, key)
    if record and record.reset_at > timestamp:
        if record.attempts >= maximum:
            return False
        record.attempts += 1
    elif record:
        record.attempts = 1
        record.reset_at = timestamp + window
    else:
        db_session.add(LoginAttemptOrm(key=key, attempts=1, reset_at=timestamp + window))
    return True
