"""Command-line entry point; business operations live in feature services."""

import argparse
from collections.abc import Callable
from typing import cast

from app import commands
from app.common.database import initialize_database
from app.common.exceptions import ApplicationError
from app.core.config import Settings

CommandHandler = Callable[[argparse.Namespace, Settings], None]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Xionzhi blog administration")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser(
        "create-admin",
        help="Create or reset an admin; password read from prompt or BLOG_ADMIN_PASSWORD",
    )
    admin.add_argument("--username", default="xionzhi")
    admin.add_argument("--reset-password", action="store_true")
    admin.add_argument("--email", help="Trusted recovery email; optional until SMTP is configured")
    bind = sub.add_parser(
        "set-admin-email",
        help="Bind an existing administrator recovery email from the trusted server console",
    )
    bind.add_argument("--username", default="xionzhi")
    bind.add_argument("--email", required=True)
    test_mail = sub.add_parser(
        "test-mail", help="Send a test mail only to the administrator bound address"
    )
    test_mail.add_argument("--username", default="xionzhi")
    backup = sub.add_parser(
        "backup", help="Create a consistent SQLite backup (copy images separately)"
    )
    backup.add_argument("file")
    admin.set_defaults(handler=commands.create_administrator)
    bind.set_defaults(handler=commands.bind_administrator_email)
    test_mail.set_defaults(handler=commands.send_test_mail)
    backup.set_defaults(handler=commands.backup_database)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        settings = Settings.from_environment()
        initialize_database(settings=settings)
        handler = cast(CommandHandler, args.handler)
        handler(args, settings)
    except (ApplicationError, ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
