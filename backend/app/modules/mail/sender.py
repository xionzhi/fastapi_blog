"""Encrypted SMTP transport; no HTTP or database dependencies."""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.core.config import Settings
from app.modules.mail.validation import validate_email_address


def send_message(config: Settings, recipient: str, subject: str, text: str, html: str = "") -> None:
    if not config.mail_enabled:
        raise ValueError("Email is not configured")
    if config.smtp_security not in ("starttls", "ssl"):
        raise ValueError("BLOG_SMTP_SECURITY must be starttls or ssl")
    sender, recipient = validate_email_address(config.mail_from), validate_email_address(recipient)
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=sender.split("@")[1])
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    if config.smtp_security == "ssl":
        client = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=15, context=context)
    else:
        client = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15)
    with client:
        client.ehlo()
        if config.smtp_security == "starttls":
            client.starttls(context=context)
            client.ehlo()
        if config.smtp_username:
            client.login(config.smtp_username, config.smtp_password.get_secret_value())
        refused = client.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
