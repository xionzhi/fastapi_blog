"""Daily aggregates and short-lived anonymous browser deduplication."""

from datetime import date
from urllib.parse import unquote, urlsplit

from pydantic import UUID4, BaseModel, Field, field_validator
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.orm import Base


class PageViewInput(BaseModel):
    path: str = Field(min_length=1, max_length=2000)
    visitor_id: UUID4
    event_id: UUID4

    @field_validator("path")
    @classmethod
    def public_path(cls, value: str) -> str:
        decoded = unquote(value)
        parsed = urlsplit(decoded)
        if (
            not decoded.startswith("/")
            or decoded.startswith("//")
            or parsed.query
            or parsed.fragment
            or "\\" in decoded
            or any(ord(char) < 32 for char in decoded)
            or any(part.startswith(".") for part in decoded.split("/"))
            or len(decoded) > 512
        ):
            raise ValueError("Use a local page path without a query string or fragment")
        return "/" + decoded.strip("/") + ("/" if decoded.strip("/") else "")


class DailyTrafficOrm(Base):
    __tablename__ = "analytics_days"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    views: Mapped[int] = mapped_column(default=0)
    visitors: Mapped[int] = mapped_column(default=0)


class PageTrafficOrm(Base):
    __tablename__ = "analytics_pages"
    day: Mapped[date] = mapped_column(
        ForeignKey("analytics_days.day", ondelete="CASCADE"), primary_key=True
    )
    path: Mapped[str] = mapped_column(String(512), primary_key=True)
    post_id: Mapped[str | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    views: Mapped[int] = mapped_column(default=0)


class DailyVisitorOrm(Base):
    __tablename__ = "analytics_visitors"
    day: Mapped[date] = mapped_column(
        ForeignKey("analytics_days.day", ondelete="CASCADE"), primary_key=True
    )
    visitor_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_event_id: Mapped[str] = mapped_column(String(32))


class DailyMetric(BaseModel):
    day: date
    views: int = 0
    visitors: int = 0


class PopularPage(BaseModel):
    path: str
    title: str
    views: int


class TrafficOverview(BaseModel):
    enabled: bool
    days: int
    timezone: str = "UTC"
    total_views: int
    average_daily_visitors: float
    today_views: int
    today_visitors: int
    daily_limit_reached: bool
    retention_days: int
    series: list[DailyMetric]
    popular_pages: list[PopularPage]
