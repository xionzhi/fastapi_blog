import re
import secrets
import smtplib
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select, update

from app.common.database import (
    connect,
)
from app.core import security as auth
from app.core.config import Settings
from app.modules.auth.models import PasswordResetOrm, UserOrm
from app.modules.mail import sender as mail


@pytest.fixture
def inbox(client, monkeypatch):
    config = client.app.state.settings
    config = config.model_copy(
        update={"smtp_host": "smtp.example.test", "mail_from": "blog@example.test"}
    )
    client.app.state.settings = config
    with connect(config) as db:
        db.execute(
            update(UserOrm).where(UserOrm.username == "writer").values(email="writer@example.test")
        )
    messages = []

    def capture(config, recipient, subject, text, html=""):
        messages.append({"to": recipient, "subject": subject, "text": text, "html": html})

    monkeypatch.setattr(mail, "send_message", capture)
    return messages


def request_token(client, inbox, identifier="writer"):
    response = client.post("/api/auth/forgot-password", json={"identifier": identifier})
    assert response.status_code == 200, response.text
    token = re.search(r"#token=([A-Za-z0-9_-]{64})", inbox[-1]["text"]).group(1)
    return token


def test_mail_unconfigured_leaves_existing_login_working(client):
    assert client.get("/api/auth/recovery").json() == {"enabled": False}
    assert (
        client.post("/api/auth/forgot-password", json={"identifier": "writer"}).status_code == 503
    )
    assert (
        client.post(
            "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
        ).status_code
        == 200
    )


def test_email_recovery_roundtrip_revokes_sessions_and_all_tokens(admin, inbox):
    token = request_token(admin, inbox)
    assert "/workspace/reset-password#token=" in inbox[0]["text"]
    unknown = admin.post("/api/auth/forgot-password", json={"identifier": "unknown"})
    known = admin.post("/api/auth/forgot-password", json={"identifier": "WRITER@example.test"})
    assert unknown.json() == known.json() and len(inbox) == 2
    assert admin.post("/api/auth/reset-password/check", json={"token": token}).json() == {
        "valid": True
    }
    with connect(admin.app.state.settings) as db:
        stored = list(db.scalars(select(PasswordResetOrm.token_hash)))
        assert auth.digest_token(token) in stored and token not in stored
    result = admin.post(
        "/api/auth/reset-password", json={"token": token, "password": "a-new-safe-password"}
    )
    assert result.status_code == 200
    assert len(inbox) == 3 and inbox[-1]["subject"].endswith("Administrator password changed")
    assert "a-new-safe-password" not in inbox[-1]["text"]
    assert admin.get("/api/admin/me").status_code == 401
    assert (
        admin.post(
            "/api/auth/reset-password", json={"token": token, "password": "another-password"}
        ).status_code
        == 400
    )
    assert (
        admin.post(
            "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
        ).status_code
        == 401
    )
    assert (
        admin.post(
            "/api/admin/login", json={"username": "writer", "password": "a-new-safe-password"}
        ).status_code
        == 200
    )
    with connect(admin.app.state.settings) as db:
        assert db.scalar(select(func.count()).select_from(PasswordResetOrm)) == 0


def test_expired_invalid_short_and_cross_origin_requests(client, inbox):
    token = request_token(client, inbox)
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": token, "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/reset-password/check",
            json={"token": token},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/forgot-password",
            json={"identifier": "writer"},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/reset-password/check", json={"token": secrets.token_urlsafe(48)}
        ).status_code
        == 400
    )
    with connect(client.app.state.settings) as db:
        db.execute(update(PasswordResetOrm).values(expires_at=int(time.time()) - 1))
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": token, "password": "another-safe-password"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
        ).status_code
        == 200
    )


def test_account_and_ip_limits_survive_identifier_variants(client, inbox):
    for identifier in ("writer", "writer@example.test", "WRITER@example.test", "writer", "writer"):
        assert (
            client.post("/api/auth/forgot-password", json={"identifier": identifier}).status_code
            == 200
        )
    assert len(inbox) == 3
    assert (
        client.post("/api/auth/forgot-password", json={"identifier": "missing"}).status_code == 429
    )


def test_a_reset_token_can_only_be_consumed_once_concurrently(client, inbox):
    token = request_token(client, inbox)
    barrier = Barrier(2)

    def reset(password):
        barrier.wait()
        return client.post(
            "/api/auth/reset-password", json={"token": token, "password": password}
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(reset, ["first-safe-password", "second-safe-password"]))
    assert sorted(codes) == [200, 400]


def test_mail_failure_invalidates_reset_token_without_logging_secrets(
    client, inbox, monkeypatch, caplog
):
    def fail(*args, **kwargs):
        raise smtplib.SMTPException("SECRET-DO-NOT-LOG")

    monkeypatch.setattr(mail, "send_message", fail)
    response = client.post("/api/auth/forgot-password", json={"identifier": "writer"})
    assert response.status_code == 200
    assert "SECRET-DO-NOT-LOG" not in caplog.text
    with connect(client.app.state.settings) as db:
        assert db.scalar(select(func.count()).select_from(PasswordResetOrm)) == 0


def test_admin_mail_test_requires_auth_and_always_uses_bound_address(admin, inbox):
    assert admin.get("/api/admin/mail").json() == {"enabled": True, "email": "writer@example.test"}
    for _ in range(3):
        assert (
            admin.post("/api/admin/mail/test", json={"to": "attacker@example.test"}).status_code
            == 200
        )
    assert all(m["to"] == "writer@example.test" for m in inbox)
    assert admin.post("/api/admin/mail/test").status_code == 429
    admin.post("/api/admin/logout")
    assert admin.post("/api/admin/mail/test").status_code == 401


@pytest.mark.parametrize("security", ["starttls", "ssl"])
def test_smtp_uses_verified_tls_and_multipart_english_mail(monkeypatch, security):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, **kwargs):
            calls.append(("connect", host, port))
            if "context" in kwargs:
                assert kwargs["context"].verify_mode == ssl.CERT_REQUIRED

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, context):
            assert context.verify_mode == ssl.CERT_REQUIRED
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login",))

        def send_message(self, message):
            assert message["To"] == "writer@example.test"
            assert message.get_content_type() == "multipart/alternative"
            calls.append(("send",))
            return {}

    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", FakeSMTP)
    cfg = Settings(
        smtp_host="smtp.example.test",
        smtp_security=security,
        smtp_username="test-user",
        smtp_password="test-secret",
        mail_from="blog@example.test",
    )
    mail.send_message(cfg, "writer@example.test", "Reset password", "Hello", "<p>Hello</p>")
    assert ("send",) in calls and ("login",) in calls
    assert (("starttls",) in calls) == (security == "starttls")
    cfg = cfg.model_copy(update={"smtp_security": "plain"})
    with pytest.raises(ValueError):
        mail.send_message(cfg, "writer@example.test", "Subject", "Text")
    cfg = cfg.model_copy(update={"smtp_security": security})
    with pytest.raises(ValueError):
        mail.send_message(cfg, "bad\r\nBcc: attacker@example.test", "Subject", "Text")
