import pytest
from fastapi.testclient import TestClient

from app.application import build_application
from app.common.database import connect
from app.common.time import utc_now
from app.core.config import Settings
from app.core.security import hash_password
from app.modules.auth.models import UserOrm


@pytest.fixture
def client(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text(
        '<!doctype html><html><head><title>Blog</title></head><body><div id="app"></div></body></html>'
    )
    config = Settings(
        data_dir=tmp_path / "data",
        site_url="http://testserver",
        allowed_origins=["http://testserver"],
        frontend_dir=frontend,
    )
    app = build_application(settings=config)
    with TestClient(app) as client:
        with connect(config) as db:
            db.add(
                UserOrm(
                    username="writer",
                    password_hash=hash_password("a-safe-test-password"),
                    created_at=utc_now(),
                    email="",
                )
            )
        yield client


@pytest.fixture
def admin(client):
    response = client.post(
        "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


@pytest.fixture
def post_data():
    return {
        "title": "Python 学习笔记",
        "slug": "python-notes",
        "body": "# Hello\n\nPython 与代码\n\n```python\nprint(1)\n```",
        "status": "published",
        "tags": ["python"],
    }
