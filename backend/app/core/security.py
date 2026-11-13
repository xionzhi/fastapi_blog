"""Password hashing, opaque tokens, and transport-level CSRF checks."""

import hashlib
import secrets

from fastapi import Request

from app.common.exceptions import ApplicationError
from app.core.config import Settings

SESSION_COOKIE = "blog_session"
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 1024
SCRYPT_N, SCRYPT_R, SCRYPT_P = 16384, 8, 5
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def hash_password(password: str) -> str:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError("Passwords must contain between 12 and 1024 characters")
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    ).hex()
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        parts = encoded.split("$")
        if len(parts) != 6:
            return False
        algorithm, cost, block, parallel, salt, expected = parts
        n, r, p = int(cost), int(block), int(parallel)
        if (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        if algorithm != "scrypt":
            return False
        if len(salt) != 32 or len(expected) != 128 or len(password) > PASSWORD_MAX_LENGTH:
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=n, r=r, p=p).hex()
        return secrets.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def session_cookie_name(settings: Settings) -> str:
    return "__Host-blog_session" if settings.is_production else SESSION_COOKIE


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return hashlib.sha256(("csrf:" + token).encode()).hexdigest()


def check_origin(*, request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in [settings.site_url, *settings.allowed_origins]:
        raise ApplicationError("Untrusted request origin", code="auth.origin", status_code=403)
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise ApplicationError(
            "Cross-site requests are not allowed", code="auth.cross_site", status_code=403
        )


def check_csrf(*, request: Request, session_token: str, settings: Settings) -> None:
    check_origin(request=request, settings=settings)
    supplied = request.headers.get("x-csrf-token", "").encode()
    expected = csrf_token(session_token).encode()
    if not secrets.compare_digest(supplied, expected):
        raise ApplicationError(
            "Your security token has expired. Reload the page.",
            code="auth.csrf",
            status_code=403,
        )
