"""Uniform error responses; validation errors never echo passwords or reset tokens."""

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.exceptions import ApplicationError

logger = logging.getLogger("blog.http")


async def application_error_handler(request: Request, error: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.message, "error_code": error.code},
        headers=error.headers,
    )


async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    details = [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in error.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": details, "error_code": "request.validation_failed"}
    )


async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    frames = traceback.extract_tb(error.__traceback__)[-5:]
    location = ";".join(
        f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}" for frame in frames
    )
    logger.error(
        "Unhandled request failure type=%s request_id=%s frames=%s",
        type(error).__name__,
        getattr(request.state, "request_id", "unknown"),
        location,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred", "error_code": "server.internal"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
