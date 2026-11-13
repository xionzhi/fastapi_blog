"""Small response contracts shared across feature APIs."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    pages: int = Field(ge=1)


class MessageResponse(BaseModel):
    message: str


class SuccessResponse(BaseModel):
    ok: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
