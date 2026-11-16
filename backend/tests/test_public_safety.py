import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event

from app.application import build_application
from app.common.database import connect
from app.core.config import Settings
from app.core.logging import BoundedFormatter, DiagnosticBudget
from app.core.rate_limit import WindowLimiter
from app.core.security import hash_password
from app.modules.auth.models import UserOrm


def production_settings(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text(
        '<html><head><title>Blog</title></head><body><div id="app"></div></body></html>'
    )
    return Settings(
        environment="production",
        site_url="https://blog.example.test",
        secure_cookies=True,
        allowed_origins=["https://blog.example.test"],
        data_dir=tmp_path / "data",
        frontend_dir=frontend,
    )


def test_production_rejects_insecure_settings(tmp_path):
    with pytest.raises(ValidationError):
        Settings(environment="production")
    with pytest.raises(ValidationError):
        Settings(
            environment="production", site_url="https://blog.example.test", secure_cookies=True
        )
    with pytest.raises(ValidationError):
        Settings(trusted_proxy_networks=["0.0.0.0/0"])
    assert production_settings(tmp_path).is_production


@pytest.mark.parametrize("enabled", [False, True])
def test_cloudflare_csp_is_opt_in_and_keeps_workspace_private(tmp_path, enabled):
    settings = production_settings(tmp_path).model_copy(
        update={"cloudflare_analytics_enabled": enabled}
    )
    with TestClient(build_application(settings=settings), base_url=settings.site_url) as client:
        response = client.get("/")
        directives = {
            values[0]: values[1:]
            for part in response.headers["content-security-policy"].split(";")
            if (values := part.split())
        }
        assert directives["script-src"] == (
            ["'self'", "https://static.cloudflareinsights.com"] if enabled else ["'self'"]
        )
        assert directives["connect-src"] == (
            ["'self'", "https://cloudflareinsights.com"] if enabled else ["'self'"]
        )
        assert directives["object-src"] == ["'none'"]
        assert "beacon.min.js" not in response.text
        for path in ("/workspace", "/workspace/login", "/workspace/reset-password"):
            policy = client.get(path).headers["content-security-policy"]
            assert "cloudflareinsights.com" not in policy
            assert "script-src 'self';" in policy


def test_cloudflare_setting_can_be_loaded_from_environment():
    settings = Settings.from_environment(environ={"BLOG_CLOUDFLARE_ANALYTICS_ENABLED": "true"})
    assert settings.cloudflare_analytics_enabled is True


def test_production_host_headers_docs_and_session_cookie(tmp_path):
    settings = production_settings(tmp_path)
    with TestClient(build_application(settings=settings), base_url=settings.site_url) as client:
        assert client.get("/api/health").headers["strict-transport-security"] == "max-age=31536000"
        assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
        with connect(settings) as session:
            from app.common.time import utc_now

            session.add(
                UserOrm(
                    username="writer",
                    password_hash=hash_password("safe-production-password"),
                    created_at=utc_now(),
                )
            )
        response = client.post(
            "/api/admin/login", json={"username": "writer", "password": "safe-production-password"}
        )
        cookie = response.headers["set-cookie"]
        assert "__Host-blog_session=" in cookie and "Secure" in cookie and "HttpOnly" in cookie
        assert "SameSite=strict" in cookie and "Domain=" not in cookie
        assert client.get("/api/admin/me").status_code == 200
        assert response.headers["cache-control"] == "no-store"


def test_forged_forwarding_headers_cannot_bypass_login_limits(client):
    for index in range(10):
        response = client.post(
            "/api/admin/login",
            json={"username": "writer", "password": "wrong"},
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/admin/login",
            json={"username": "writer", "password": "wrong"},
            headers={"X-Forwarded-For": "203.0.113.99"},
        ).status_code
        == 429
    )


def test_scanner_rejection_does_not_open_database_connections(client):
    calls = []
    engine = client.app.state.database.engine

    def capture(*args):
        calls.append(args)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        for path in ("/.env", "/.git/config", "/wp-login.php", "/admin/../../.env"):
            assert client.get(path).status_code == 404
        assert client.get("/api/posts?q=" + "x" * 2100).status_code == 414
        assert not calls
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_small_public_payload_limits_and_burst_rejection(client):
    assert client.post("/api/admin/login", content=b"x" * 8193).status_code == 413
    assert client.post("/api/analytics/events", content=b"x" * 2049).status_code == 413
    for _ in range(120):
        assert client.get("/api/health").status_code == 200
    blocked = client.get("/api/health")
    assert blocked.status_code == 429 and blocked.headers["retry-after"] == "60"


def test_limiter_memory_and_diagnostic_output_are_bounded(monkeypatch):
    limiter = WindowLimiter(capacity=32)
    for index in range(1000):
        assert limiter.allow(f"client-{index}", maximum=1, seconds=60)
    assert len(limiter.windows) == 32
    clock = [0.0]
    monkeypatch.setattr("app.core.logging.time.monotonic", lambda: clock[0])
    budget = DiagnosticBudget(maximum=3)
    formatter = BoundedFormatter()
    emitted = []
    for _ in range(1000):
        record = logging.LogRecord(
            "blog.http",
            logging.ERROR,
            __file__,
            1,
            "safe\n" + "x" * 5000,
            (),
            (ValueError, ValueError("PRIVATE-ERROR-DATA"), None),
        )
        if budget.filter(record):
            emitted.append(formatter.format(record))
    assert len(emitted) == 3
    assert all(
        len(line) <= 2048 and "\n" not in line and "PRIVATE-ERROR-DATA" not in line
        for line in emitted
    )
    clock[0] = 61
    record = logging.LogRecord("blog.http", logging.ERROR, __file__, 1, "next", (), None)
    assert budget.filter(record)
    assert "suppressed_previous_window=997" in formatter.format(record)


def test_public_compression_cache_and_image_range(tmp_path):
    settings = production_settings(tmp_path)
    image_name = "a" * 32 + ".png"
    settings.images.mkdir(parents=True)
    (settings.images / image_name).write_bytes(b"image-bytes-for-range-testing")
    with TestClient(build_application(settings=settings), base_url=settings.site_url) as client:
        image = client.get("/content/images/" + image_name)
        assert image.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert "content-encoding" not in image.headers
        cached = client.get(
            "/content/images/" + image_name, headers={"If-None-Match": image.headers["etag"]}
        )
        assert cached.status_code == 304
        partial = client.get("/content/images/" + image_name, headers={"Range": "bytes=0-4"})
        assert partial.status_code == 206 and partial.content == b"image"
        assert "content-encoding" not in partial.headers
        public = client.get("/api/site")
        assert public.headers["cache-control"].startswith("public, max-age=30")


def test_paginated_lists_defer_article_bodies_and_details_are_compressed(admin, post_data):
    body = "Readable content and code notes. " * 2000
    created = admin.post("/api/admin/posts", json={**post_data, "body": body}).json()
    statements = []
    engine = admin.app.state.database.engine

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        public = admin.get("/api/posts").json()["items"][0]
        protected = admin.get("/api/admin/posts").json()["items"][0]
        assert "body" not in public and "html" not in public
        assert "body" not in protected and "html" not in protected
        for statement in statements:
            if statement.lstrip().lower().startswith("select count("):
                continue
            assert "posts.body" not in statement and "posts.html" not in statement
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    detail = admin.get("/api/posts/" + created["slug"])
    assert detail.headers["content-encoding"] == "gzip"
    assert "Readable content" in detail.json()["html"]
    assert admin.get("/api/admin/posts/" + created["id"]).json()["body"] == body
