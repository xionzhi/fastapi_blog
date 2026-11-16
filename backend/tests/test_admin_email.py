import time

import pytest
from sqlalchemy import delete, select

from app.common.database import connect
from app.core.security import digest_token
from app.modules.auth import administration
from app.modules.auth.models import LoginAttemptOrm, PasswordResetOrm, SessionOrm, UserOrm
from app.modules.mail import sender


def change_email(admin, email="new@example.test", previous="", password="a-safe-test-password"):
    return admin.put(
        "/api/admin/mail",
        json={"email": email, "previous_email": previous, "current_password": password},
    )


def seed_security_records(admin):
    with connect(admin.app.state.settings) as db:
        user = db.scalar(select(UserOrm).where(UserOrm.username == "writer"))
        db.add(SessionOrm(token_hash="1" * 64, user_id=user.id, expires_at=int(time.time()) + 3600))
        db.add(
            PasswordResetOrm(
                token_hash="2" * 64,
                user_id=user.id,
                expires_at=int(time.time()) + 900,
                created_at=int(time.time()),
            )
        )
        return user.password_hash


@pytest.fixture
def email_inbox(admin, monkeypatch):
    config = admin.app.state.settings.model_copy(
        update={"smtp_host": "smtp.example.test", "mail_from": "blog@example.test"}
    )
    admin.app.state.settings = config
    with connect(config) as db:
        db.scalar(select(UserOrm).where(UserOrm.username == "writer")).email = "old@example.test"
    messages = []

    def capture(config, recipient, subject, text, html=""):
        messages.append({"to": recipient, "subject": subject, "text": text})

    monkeypatch.setattr(sender, "send_message", capture)
    return messages


def test_bind_without_smtp_revokes_old_links_and_other_sessions(admin, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No live email is allowed")

    monkeypatch.setattr(sender, "send_message", forbidden)
    original_hash = seed_security_records(admin)
    response = change_email(admin)
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "email": "new@example.test"}
    assert admin.get("/api/admin/me").status_code == 200
    with connect(admin.app.state.settings) as db:
        user = db.scalar(select(UserOrm).where(UserOrm.username == "writer"))
        assert user.email == "new@example.test" and user.password_hash == original_hash
        assert list(db.scalars(select(PasswordResetOrm))) == []
        assert list(db.scalars(select(SessionOrm.token_hash))) == [
            digest_token(admin.cookies.get("blog_session"))
        ]


def test_change_notifies_old_address_with_mock_transport(admin, email_inbox):
    seed_security_records(admin)
    response = change_email(admin, previous="old@example.test")
    assert response.status_code == 200
    assert admin.get("/api/admin/mail").json() == {"enabled": True, "email": "new@example.test"}
    assert len(email_inbox) == 1 and email_inbox[0]["to"] == "old@example.test"
    assert "recovery email changed" in email_inbox[0]["subject"]
    assert "a-safe-test-password" not in email_inbox[0]["text"]
    assert admin.post("/api/admin/mail/test").status_code == 200
    assert email_inbox[-1]["to"] == "new@example.test"


def test_wrong_password_is_bounded_and_does_not_log_out_current_session(admin):
    seed_security_records(admin)
    for _ in range(5):
        response = change_email(admin, password="incorrect-current-password")
        assert response.status_code == 403
        assert response.json()["error_code"] == "auth.invalid_password"
    response = change_email(admin)
    assert response.status_code == 429 and response.headers["retry-after"] == "900"
    assert admin.get("/api/admin/me").status_code == 200
    with connect(admin.app.state.settings) as db:
        assert db.scalar(select(UserOrm.email)) == ""
        assert len(list(db.scalars(select(SessionOrm)))) == 2
        assert len(list(db.scalars(select(PasswordResetOrm)))) == 1
        limit = db.scalar(select(LoginAttemptOrm).where(LoginAttemptOrm.key.like("email-change:%")))
        assert limit.attempts == 5
        limit.reset_at = int(time.time()) - 1
    assert change_email(admin).status_code == 200


def test_email_change_requires_authentication_csrf_and_trusted_origin(client, admin):
    csrf = admin.headers.pop("X-CSRF-Token")
    assert change_email(admin).status_code == 403
    admin.headers["X-CSRF-Token"] = csrf
    assert (
        admin.put(
            "/api/admin/mail",
            json={
                "email": "new@example.test",
                "previous_email": "",
                "current_password": "a-safe-test-password",
            },
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    admin.post("/api/admin/logout")
    assert change_email(client).status_code == 401


def test_duplicate_email_rolls_back_reset_and_session_changes(admin):
    seed_security_records(admin)
    with connect(admin.app.state.settings) as db:
        db.add(
            UserOrm(
                username="other",
                password_hash="unused-test-hash",
                email="taken@example.test",
                created_at=db.scalar(select(UserOrm.created_at)),
            )
        )
    assert change_email(admin, email="TAKEN@example.test").status_code == 409
    with connect(admin.app.state.settings) as db:
        assert db.scalar(select(UserOrm.email).where(UserOrm.username == "writer")) == ""
        assert len(list(db.scalars(select(SessionOrm)))) == 2
        assert len(list(db.scalars(select(PasswordResetOrm)))) == 1


def test_stale_edit_is_rejected_and_repeat_save_is_a_noop(admin, email_inbox):
    seed_security_records(admin)
    assert change_email(admin, previous="stale@example.test").status_code == 409
    assert change_email(admin, previous="old@example.test").status_code == 200
    seed_security_records(admin)
    assert change_email(admin, previous="old@example.test").status_code == 200
    assert len(email_inbox) == 1
    with connect(admin.app.state.settings) as db:
        assert len(list(db.scalars(select(SessionOrm)))) == 2
        assert len(list(db.scalars(select(PasswordResetOrm)))) == 1


@pytest.mark.parametrize("email", ["", "not-an-email", "a@example.test\r\nBcc: b@example.test"])
def test_invalid_email_is_rejected_without_echoing_password(admin, email):
    response = change_email(admin, email=email, password="PRIVATE-CURRENT-PASSWORD")
    assert response.status_code == 422
    assert "PRIVATE-CURRENT-PASSWORD" not in response.text
    assert admin.get("/api/admin/mail").json()["email"] == ""


def test_mail_change_has_a_small_request_limit(admin):
    assert change_email(admin, password="x" * 9000).status_code == 413


def test_mail_failure_does_not_undo_email_change(admin, email_inbox, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE-SMTP-ERROR")

    monkeypatch.setattr(sender, "send_message", fail)
    assert change_email(admin, previous="old@example.test").status_code == 200
    assert admin.get("/api/admin/mail").json()["email"] == "new@example.test"
    assert "PRIVATE-SMTP-ERROR" not in caplog.text


def test_credentials_revoked_during_password_verification_prevent_the_change(admin, monkeypatch):
    original_verify = administration.verify_password

    def revoke(password, encoded):
        verified = original_verify(password, encoded)
        with connect(admin.app.state.settings) as db:
            db.execute(delete(SessionOrm))
        return verified

    monkeypatch.setattr(administration, "verify_password", revoke)
    assert change_email(admin).status_code == 401
    with connect(admin.app.state.settings) as db:
        assert db.scalar(select(UserOrm.email)) == ""
