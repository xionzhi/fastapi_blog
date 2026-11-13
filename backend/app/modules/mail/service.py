"""Administrator email workflows. Credentials and email bodies are never logged."""

import logging
import time
from html import escape

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.common.database import begin_write, connect, read_settings
from app.common.exceptions import ApplicationError, RateLimitError
from app.core.config import Settings
from app.core.paths import WORKSPACE_PATH
from app.modules.auth.models import CurrentUser, PasswordResetOrm
from app.modules.auth.rate_limit import consume_limit
from app.modules.mail import sender
from app.modules.mail.models import MailStatus

logger = logging.getLogger("blog.mail")


def get_status(*, settings: Settings, user: CurrentUser) -> MailStatus:
    return MailStatus(enabled=settings.mail_enabled, email=user.email)


def test_delivery(*, db_session: Session, settings: Settings, user: CurrentUser) -> None:
    if not settings.mail_enabled:
        raise ApplicationError("Email is not configured.", code="mail.disabled", status_code=503)
    if not user.email:
        raise ApplicationError(
            "This administrator does not have a recovery email.",
            code="mail.address_missing",
            status_code=422,
        )
    begin_write(db_session)
    allowed = consume_limit(
        db_session, "mail-test:" + str(user.id), int(time.time()), maximum=3, window=900
    )
    db_session.commit()
    if not allowed:
        raise RateLimitError("Too many test emails. Please try again in 15 minutes.")
    try:
        title = site_title(settings)
        sender.send_message(
            settings,
            user.email,
            f"[{title}] Email service test",
            f"This is an administrator test email. Receiving it confirms SMTP submission.\n\nBlog URL: {settings.site_url}",
        )
    except Exception as exc:
        logger.error("SMTP test failed (%s)", type(exc).__name__)
        raise ApplicationError(
            "Email submission failed. Check the server SMTP configuration and mail logs.",
            code="mail.delivery_failed",
            status_code=502,
        ) from None


def site_title(config: Settings) -> str:
    with connect(config) as db:
        return str(read_settings(db)["title"])


def password_changed(config: Settings, recipient: str, username: str) -> None:
    if not config.mail_enabled or not recipient:
        return
    title = site_title(config)
    try:
        sender.send_message(
            config,
            recipient,
            f"[{title}] Administrator password changed",
            f"Hello {username},\n\nYour blog administrator password has changed. All previous sessions and reset links have been revoked.\n"
            f"If you did not make this change, reset your password from the server console and check your recovery email immediately.\n\nBlog: {config.site_url}\n\nThis email does not contain your password.",
        )
    except Exception as exc:
        # SMTP errors can contain credentials, recipients or body fragments; never log them verbatim.
        logger.error("Password-change notification failed (%s)", type(exc).__name__)


def send_reset(config: Settings, recipient: str, username: str, token: str) -> None:
    from app.core.security import digest_token

    title = site_title(config)
    # Fragment is not included in HTTP access logs or Referer headers.
    link = config.site_url + WORKSPACE_PATH + "/reset-password#token=" + token
    try:
        sender.send_message(
            config,
            recipient,
            f"[{title}] Reset your administrator password",
            f"Hello {username},\n\nOpen this link to reset your blog password. It expires in 15 minutes and can only be used once:\n\n{link}\n\n"
            "If you did not request a password reset, ignore this email. Your password and current sessions will remain unchanged.",
            f"<p>Hello {escape(username)},</p><p>You requested a new blog administrator password. This link <strong>expires in 15 minutes</strong> and can only be used once.</p>"
            f'<p><a href="{escape(link, quote=True)}">Reset password</a></p><p>If the button does not work, copy this address into your browser:</p><p>{escape(link)}</p>'
            "<p>If you did not request this, ignore this email. Your password and current sessions will remain unchanged.</p>",
        )
    except Exception as exc:
        with connect(config) as db:
            db.execute(
                delete(PasswordResetOrm).where(PasswordResetOrm.token_hash == digest_token(token))
            )
        logger.error("Password-reset mail failed; token invalidated (%s)", type(exc).__name__)
