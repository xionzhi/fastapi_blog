"""Regression checks for the boundaries established during the engineering refactor."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.application import build_application
from app.core.config import Settings


def test_application_assembly_has_no_database_side_effects(tmp_path):
    settings = Settings(data_dir=tmp_path / "not-created-yet")
    application = build_application(settings=settings)
    assert not settings.data_dir.exists()
    with TestClient(application) as client:
        assert client.get("/api/health").status_code == 200
        assert settings.database.exists()


def test_settings_validate_origins_tls_and_redact_credentials():
    with pytest.raises(ValidationError):
        Settings(allowed_origins=["*"])
    with pytest.raises(ValidationError):
        Settings(smtp_security="plain")
    with pytest.raises(ValidationError):
        Settings(smtp_host="smtp.example.test")
    configured = Settings(
        smtp_host="smtp.example.test",
        mail_from="writer@example.test",
        smtp_username="writer",
        smtp_password="never-display-this-secret",
    )
    assert "never-display-this-secret" not in repr(configured)


def test_validation_errors_never_echo_recovery_credentials(client):
    secret = "PRIVATE-RESET-CREDENTIAL"
    response = client.post("/api/auth/reset-password", json={"token": secret, "password": secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert response.json()["error_code"] == "request.validation_failed"


def test_chunked_request_limit_is_enforced_without_content_length(tmp_path):
    application = build_application(settings=Settings(data_dir=tmp_path, max_request_bytes=1024))
    with TestClient(application) as client:
        response = client.post(
            "/api/admin/login",
            content=iter([b"{" + b" " * 1200, b"}"]),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 413


def test_business_services_do_not_use_sql_strings_or_http_exceptions():
    modules = Path(__file__).resolve().parents[1] / "app" / "modules"
    for path in modules.rglob("*.py"):
        if path.name in {"views.py", "dependencies.py"} or path.parent.name in {
            "publishing",
            "health",
        }:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "sqlite3", path
                assert node.module != "fastapi", path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"execute", "executemany", "executescript"} and node.args:
                    assert not isinstance(node.args[0], (ast.Constant, ast.JoinedStr)), path
