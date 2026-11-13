"""Validated configuration loaded explicitly by the executable entry points."""

import os
from collections.abc import Mapping
from ipaddress import ip_network
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    """Application settings; construction performs no filesystem or network writes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: Literal["development", "production"] = "development"
    data_dir: Path = PROJECT_ROOT / "data" / "dev"
    frontend_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    site_url: str = "http://127.0.0.1:8000"
    secure_cookies: bool = False
    session_hours: int = Field(default=24, ge=1, le=720)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = Field(default_factory=lambda: SecretStr(""))
    smtp_security: Literal["starttls", "ssl"] = "starttls"
    mail_from: str = ""
    max_request_bytes: int = Field(default=32 * 1024 * 1024, ge=1024)
    trusted_proxy_networks: list[str] = Field(default_factory=list)
    analytics_enabled: bool = True
    analytics_retention_days: int = Field(default=90, ge=7, le=365)
    analytics_max_daily_views: int = Field(default=50_000, ge=100, le=1_000_000)

    @field_validator("trusted_proxy_networks")
    @classmethod
    def validate_proxy_networks(cls, values: list[str]) -> list[str]:
        networks = [ip_network(value, strict=False) for value in values]
        if any(network.prefixlen == 0 for network in networks):
            raise ValueError("Trust only explicit reverse proxy addresses or private networks")
        return [str(network) for network in networks]

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        if self.environment == "production":
            if not self.site_url.startswith("https://") or not self.secure_cookies:
                raise ValueError("Production requires an HTTPS BLOG_URL and secure session cookies")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production frontend origins must use HTTPS")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def allowed_hosts(self) -> list[str]:
        hosts = {
            urlsplit(origin).hostname or "" for origin in [self.site_url, *self.allowed_origins]
        }
        hosts.update({"localhost", "127.0.0.1"})
        if not self.is_production:
            hosts.add("testserver")
        return sorted(hosts - {""})

    @field_validator("data_dir", "frontend_dir")
    @classmethod
    def resolve_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("BLOG_URL must be an absolute HTTP(S) origin")
        if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("BLOG_URL must not contain credentials, a path, or query parameters")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(cls.validate_site_url(value) for value in values))

    @model_validator(mode="after")
    def validate_mail_settings(self) -> Self:
        if bool(self.smtp_host) != bool(self.mail_from):
            raise ValueError("Set BLOG_SMTP_HOST and BLOG_MAIL_FROM together")
        if self.smtp_username and not self.smtp_password.get_secret_value():
            raise ValueError("BLOG_SMTP_PASSWORD is required when an SMTP username is set")
        if self.mail_from:
            from app.modules.mail.validation import validate_email_address

            validate_email_address(self.mail_from)
        return self

    @property
    def database(self) -> Path:
        return self.data_dir / "blog.sqlite3"

    @property
    def images(self) -> Path:
        return self.data_dir / "images"

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host and self.mail_from)

    @classmethod
    def from_environment(cls, *, environ: Mapping[str, str] | None = None) -> Self:
        """Read .env without modifying process-global environment variables."""
        values = dict(dotenv_values(PROJECT_ROOT / ".env"))
        values.update(os.environ if environ is None else environ)
        names = {
            "environment": "BLOG_ENVIRONMENT",
            "data_dir": "BLOG_DATA_DIR",
            "site_url": "BLOG_URL",
            "secure_cookies": "BLOG_SECURE_COOKIES",
            "session_hours": "BLOG_SESSION_HOURS",
            "smtp_host": "BLOG_SMTP_HOST",
            "smtp_port": "BLOG_SMTP_PORT",
            "smtp_username": "BLOG_SMTP_USERNAME",
            "smtp_password": "BLOG_SMTP_PASSWORD",
            "smtp_security": "BLOG_SMTP_SECURITY",
            "mail_from": "BLOG_MAIL_FROM",
            "analytics_enabled": "BLOG_ANALYTICS_ENABLED",
            "analytics_retention_days": "BLOG_ANALYTICS_RETENTION_DAYS",
            "analytics_max_daily_views": "BLOG_ANALYTICS_MAX_DAILY_VIEWS",
        }
        data: dict[str, object] = {
            field: values[name] for field, name in names.items() if values.get(name)
        }
        if origins := values.get("BLOG_ALLOWED_ORIGINS"):
            data["allowed_origins"] = [
                value.strip() for value in origins.split(",") if value.strip()
            ]
        if proxies := values.get("BLOG_TRUSTED_PROXY_NETWORKS"):
            data["trusted_proxy_networks"] = [
                value.strip() for value in proxies.split(",") if value.strip()
            ]
        return cls.model_validate(data)
