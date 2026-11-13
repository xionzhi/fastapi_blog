from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.orm import Base
from app.modules.post.content import validate_slug


class TagInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)

    _slug = field_validator("slug")(validate_slug)


class TagRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str = ""
    count: int | None = None


class TagOrm(Base):
    __tablename__ = "tags"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
