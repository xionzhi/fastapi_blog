from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.models import Page


class UploadedImage(BaseModel):
    url: str


class ImageRead(BaseModel):
    src: str
    width: int
    height: int
    srcset: str = ""
    sizes: str = ""


class ImageUsage(BaseModel):
    title: str
    url: str


class LibraryImage(BaseModel):
    path: str
    name: str
    url: str
    thumbnail: str
    size: int
    modified_at: datetime
    revision: str
    usages: list[ImageUsage] = Field(default_factory=list)


ImageLibrary = Page[LibraryImage]


class ImageSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=500)
    revision: str = Field(pattern=r"^[a-f0-9]{32}$")


class ImageMove(ImageSelection):
    new_path: str = Field(min_length=1, max_length=500)


class ImageMoveResult(BaseModel):
    image: LibraryImage
    source_retained: bool = False
