"""Bounded diagnostics: no access log, sampled warnings/errors, and no exception payloads."""

import copy
import logging
import logging.config
import time
from threading import Lock


class DiagnosticBudget(logging.Filter):
    def __init__(self, *, maximum: int = 10, window_seconds: int = 60) -> None:
        super().__init__()
        self.maximum = maximum
        self.window_seconds = window_seconds
        self.started = time.monotonic()
        self.emitted = 0
        self.suppressed = 0
        self.lock = Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        record.suppressed_count = 0
        if record.levelno < logging.WARNING:
            return True
        with self.lock:
            now = time.monotonic()
            if now - self.started >= self.window_seconds:
                record.suppressed_count = self.suppressed
                self.started, self.emitted, self.suppressed = now, 0, 0
            if self.emitted >= self.maximum:
                self.suppressed += 1
                return False
            self.emitted += 1
            return True


class BoundedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        safe_record = copy.copy(record)
        if safe_record.exc_info:
            exception = safe_record.exc_info[1]
            safe_record.msg = (
                f"{safe_record.getMessage()} exception_type={type(exception).__name__}"
            )
            safe_record.args = ()
            safe_record.exc_info = None
            safe_record.exc_text = None
        safe_record.stack_info = None
        message = super().format(safe_record).replace("\r", "\\r").replace("\n", "\\n")
        suppressed = getattr(safe_record, "suppressed_count", 0)
        if suppressed:
            message = f"suppressed_previous_window={suppressed} {message}"
        return message.encode("utf-8")[:2048].decode("utf-8", errors="ignore")


def configure_logging() -> None:
    logging.captureWarnings(True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"budget": {"()": DiagnosticBudget}},
            "formatters": {
                "bounded": {
                    "()": BoundedFormatter,
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "bounded",
                    "filters": ["budget"],
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
            "loggers": {
                "uvicorn": {"handlers": ["console"], "propagate": False, "level": "INFO"},
                "uvicorn.error": {"handlers": ["console"], "propagate": False, "level": "INFO"},
                "uvicorn.access": {"handlers": [], "propagate": False, "level": "CRITICAL"},
            },
        }
    )
