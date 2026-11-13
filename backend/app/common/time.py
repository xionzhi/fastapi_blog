"""UTC timestamps shared by storage and serialization."""

from datetime import UTC, datetime


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def utc_now() -> datetime:
    return datetime.now(UTC)
