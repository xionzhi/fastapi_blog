"""Exercise every protected operation through the assembled HTTP application."""

import re
import time

import pytest
from sqlalchemy import event, select
from starlette.requests import Request

from app.common.database import connect
from app.core.security import digest_token
from app.modules.auth.models import SessionOrm


def admin_operations(client, *, writes_only=False):
    operations = []
    for path, methods in client.app.openapi()["paths"].items():
        if not path.startswith("/api/admin/") or path == "/api/admin/login":
            continue
        for method in methods:
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if writes_only and method == "get":
                continue
            url = re.sub(r"\{[^}]+\}", "a" * 32, path)
            operations.append((method.upper(), url))
    assert len(operations) >= (12 if writes_only else 20)
    return operations


def denied_request(client, method, path, *, headers=None):
    query = {"path": "fixture.png", "sha256": "0" * 64}
    if path == "/api/admin/images" and method == "POST":
        return client.request(
            method,
            path,
            params=query,
            content=b"intentionally malformed multipart data",
            headers={"Content-Type": "multipart/form-data; boundary=fixture", **(headers or {})},
        )
    return client.request(method, path, params=query, json={}, headers=headers)


def test_every_administrator_operation_rejects_anonymous_requests(client):
    for method, path in admin_operations(client):
        response = denied_request(client, method, path)
        assert response.status_code == 401, (method, path, response.text)
        assert response.json()["error_code"] == "auth.unauthorized"
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({"X-CSRF-Token": ""}, "auth.csrf"),
        ({"X-CSRF-Token": "forged-token"}, "auth.csrf"),
        ({"Origin": "https://untrusted.example"}, "auth.origin"),
        ({"Sec-Fetch-Site": "cross-site"}, "auth.cross_site"),
    ],
)
def test_every_administrator_write_checks_csrf_and_origin(admin, headers, code):
    for method, path in admin_operations(admin, writes_only=True):
        response = denied_request(admin, method, path, headers=headers)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["error_code"] == code


@pytest.mark.parametrize("state", ["expired", "revoked", "forged"])
def test_invalid_sessions_cannot_replay_any_administrator_operation(admin, state):
    token = admin.cookies.get("blog_session")
    if state == "expired":
        with connect(admin.app.state.settings) as session:
            stored = session.scalar(
                select(SessionOrm).where(SessionOrm.token_hash == digest_token(token))
            )
            stored.expires_at = int(time.time()) - 1
    elif state == "revoked":
        assert admin.post("/api/admin/logout").status_code == 200
    else:
        token = "x" * 64
    for method, path in admin_operations(admin):
        response = denied_request(admin, method, path, headers={"Cookie": f"blog_session={token}"})
        assert response.status_code == 401, (state, method, path, response.text)


def test_missing_and_malformed_session_tokens_do_not_query_the_database(client):
    queries = []
    engine = client.app.state.database.engine

    def capture(*args):
        queries.append(args)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        for token in ("", "invalid", "x" * 65, "!" * 64):
            response = client.get("/api/admin/me", headers={"Cookie": f"blog_session={token}"})
            assert response.status_code == 401
        assert not queries
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_image_upload_checks_session_and_csrf_before_parsing_multipart(client, admin, monkeypatch):
    body = client.app.openapi()["paths"]["/api/admin/images"]["post"]["requestBody"]
    assert body["content"]["multipart/form-data"]["schema"]["properties"]["file"] == {
        "type": "string",
        "format": "binary",
    }

    def refuse_form(*args, **kwargs):
        raise AssertionError("Unauthorized multipart content must not be parsed")

    monkeypatch.setattr(Request, "form", refuse_form)
    response = denied_request(admin, "POST", "/api/admin/images", headers={"X-CSRF-Token": ""})
    assert response.status_code == 403
    admin.cookies.clear()
    response = denied_request(client, "POST", "/api/admin/images")
    assert response.status_code == 401


@pytest.mark.parametrize("filename", ["notes.txt", "backup.sqlite3", "page.html", "image.svg"])
def test_image_directory_does_not_publish_non_image_files(client, filename):
    path = client.app.state.settings.images / filename
    path.write_text("private fixture content", encoding="utf-8")
    for method in ("GET", "HEAD"):
        response = client.request(method, f"/content/images/{filename}")
        assert response.status_code == 404
        assert b"private fixture content" not in response.content
    assert client.get(f"/content/images/{filename}?width=96").status_code == 404
