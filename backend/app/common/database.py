"""SQLAlchemy sessions, SQLite connection policy, and Alembic schema ownership."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[2] / "migrations"


def load_model_metadata() -> None:
    from app.modules.analytics import models as analytics_models
    from app.modules.auth import models as auth_models
    from app.modules.post import models as post_models
    from app.modules.site import models as site_models
    from app.modules.tag import models as tag_models

    _ = (analytics_models, auth_models, post_models, site_models, tag_models)


def create_database_engine(settings: Settings) -> Engine:
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(settings.database)),
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def configure_connection(connection: sqlite3.Connection, connection_record: object) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


class Database:
    """One engine per application, with one unit of work per request or command."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_database_engine(settings)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    def initialize(self) -> None:
        load_model_metadata()
        self.settings.images.mkdir(parents=True, exist_ok=True)
        configuration = AlembicConfig()
        configuration.set_main_option("script_location", str(MIGRATIONS_DIRECTORY))
        with self.engine.begin() as connection:
            # Serialize SQLite startup migrations and make DDL part of the same transaction.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            configuration.attributes["connection"] = connection
            command.upgrade(configuration, "head")
        from app.modules.site.defaults import DEFAULTS
        from app.modules.site.models import SiteSettingOrm

        with self.session() as session:
            known = set(session.scalars(select(SiteSettingOrm.key)))
            session.add_all(
                SiteSettingOrm(key=key, value=value)
                for key, value in DEFAULTS.items()
                if key not in known
            )

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def dispose(self) -> None:
        self.engine.dispose()


@contextmanager
def connect(settings: Settings) -> Iterator[Session]:
    database = Database(settings)
    try:
        with database.session() as session:
            yield session
    finally:
        database.dispose()


def initialize_database(*, settings: Settings) -> None:
    database = Database(settings)
    try:
        database.initialize()
    finally:
        database.dispose()


def begin_write(session: Session) -> None:
    """SQLite transaction control only; all business reads and writes use mapped entities."""
    session.connection().exec_driver_sql("BEGIN IMMEDIATE")


def begin_snapshot(session: Session) -> None:
    """Pin an explicit SQLite read snapshot across the tables in a content export."""
    session.connection().exec_driver_sql("BEGIN")


def read_settings(session: Session) -> dict[str, Any]:
    from app.modules.site.models import SiteSettingOrm

    return {setting.key: setting.value for setting in session.scalars(select(SiteSettingOrm))}


def backup_database(*, session: Session, destination: Path) -> None:
    connection = cast(sqlite3.Connection, session.connection().connection.driver_connection)
    with sqlite3.connect(destination) as target:
        connection.backup(target)
