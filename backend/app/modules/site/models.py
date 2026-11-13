from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.orm import Base
from app.modules.post.content import safe_url


class Navigation(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    url: str = Field(max_length=2000)

    _url = field_validator("url")(safe_url)


class SiteInput(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    cover: str = Field(default="", max_length=2000)
    logo: str = Field(default="", max_length=2000)
    author: str = Field(default="xionzhi", min_length=1, max_length=100)
    author_image: str = Field(default="", max_length=2000)
    author_bio: str = Field(default="", max_length=500)
    posts_per_page: int = Field(default=5, ge=1, le=30)
    navigation: list[Navigation] = Field(default_factory=list, max_length=10)

    @field_validator("cover", "logo", "author_image")
    @classmethod
    def url_valid(cls, v: str) -> str:
        return safe_url(v)


class SiteStats(BaseModel):
    posts: int
    tags: int


class SiteRead(SiteInput):
    stats: SiteStats | None = None


class SiteSettingOrm(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
