"""Mailbox validation shared by deployment configuration and administration."""

import re


def validate_email_address(value: str) -> str:
    value = value.strip()
    # A single ASCII mailbox, not a display name or recipient list. Prevent header injection.
    if len(value) > 254 or not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}",
        value,
    ):
        raise ValueError("Enter a valid email address")
    local, domain = value.rsplit("@", 1)
    if len(local) > 64 or ".." in value or local.startswith(".") or local.endswith("."):
        raise ValueError("Enter a valid email address")
    return local + "@" + domain.lower()
