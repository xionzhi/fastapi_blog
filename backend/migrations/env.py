"""Alembic environment, also used programmatically by the application lifecycle."""

from alembic import context
from sqlalchemy import create_engine

from app.common.orm import Base
from app.core.config import Settings


def run_migrations() -> None:
    from app.common.database import load_model_metadata

    load_model_metadata()
    supplied_connection = context.config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(connection=supplied_connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(f"sqlite+pysqlite:///{Settings.from_environment().database.as_posix()}")
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
