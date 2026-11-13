"""Typed request-scoped SQLAlchemy session and configuration dependencies."""

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.common.database import Database
from app.core.config import Settings


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_db_session(request: Request) -> Iterator[Session]:
    database = cast(Database, request.app.state.database)
    with database.session() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db_session, scope="function")]
