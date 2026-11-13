"""Hourly retention cleanup; no background request logging or unbounded event queue."""

import asyncio
import logging

from app.common.database import Database, begin_write
from app.modules.analytics import service as analytics
from app.modules.auth import service as auth

logger = logging.getLogger("blog.maintenance")


def run_maintenance(database: Database) -> None:
    with database.session() as session:
        begin_write(session)
        analytics.purge_expired(session=session, settings=database.settings)
        auth.purge_expired(session=session)


async def periodic_maintenance(database: Database) -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            await asyncio.to_thread(run_maintenance, database)
        except Exception as error:
            logger.warning("Retention cleanup failed type=%s", type(error).__name__)
