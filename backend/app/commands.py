"""CLI handlers. Argument parsing is separate from account and storage services."""

import argparse
import getpass
import os
from pathlib import Path

from app.common.database import backup_database as write_database_backup
from app.common.database import connect
from app.core.config import Settings
from app.modules.auth import administration
from app.modules.mail import sender
from app.modules.mail import service as mail_service


def create_administrator(args: argparse.Namespace, settings: Settings) -> None:
    password = os.getenv("BLOG_ADMIN_PASSWORD") or getpass.getpass(
        "New admin password (12+ characters): "
    )
    if not os.getenv("BLOG_ADMIN_PASSWORD") and password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match")
    with connect(settings) as db_session:
        previous_user = administration.save_administrator(
            db_session=db_session,
            username=args.username,
            password=password,
            email=args.email or "",
            reset_password=args.reset_password,
        )
    if previous_user and previous_user.email:
        mail_service.password_changed(settings, previous_user.email, previous_user.username)
    print(f"Admin ready: {args.username}")


def bind_administrator_email(args: argparse.Namespace, settings: Settings) -> None:
    with connect(settings) as db_session:
        administration.bind_email(db_session=db_session, username=args.username, email=args.email)
    print("Administrator recovery email bound; old reset links invalidated.")


def send_test_mail(args: argparse.Namespace, settings: Settings) -> None:
    with connect(settings) as db_session:
        user = administration.get_administrator(db_session=db_session, username=args.username)
    if not user.email:
        raise ValueError("Bind a recovery email first with set-admin-email")
    try:
        sender.send_message(
            settings,
            user.email,
            "[Blog] Administrator email test",
            f"SMTP email submission test.\nBlog URL: {settings.site_url}",
        )
    except Exception as exc:
        raise ValueError(
            f"SMTP test failed ({type(exc).__name__}); check server configuration"
        ) from None
    print("Test mail submitted. Check your inbox and spam folder.")


def backup_database(args: argparse.Namespace, settings: Settings) -> None:
    target = Path(args.file).resolve()
    if target == settings.database or target.exists():
        raise ValueError("Backup target must be a new file outside the live database")
    with connect(settings) as source:
        write_database_backup(session=source, destination=target)
    print(f"Backup created: {target}")
