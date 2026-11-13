"""ASGI entry point used by Uvicorn. Importing it does not initialize storage."""

from app.application import build_application
from app.core.config import Settings
from app.core.logging import configure_logging

configure_logging()
app = build_application(settings=Settings.from_environment())
