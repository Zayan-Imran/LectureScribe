"""Logging configuration for LectureScribe."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

from lecturescribe import __app_name__

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure console and file logging for the desktop application."""
    log_dir = Path.home() / "AppData" / "Local" / __app_name__ / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": LOG_FORMAT,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "standard",
                    "filename": log_dir / "lecturescribe.log",
                    "maxBytes": 1_000_000,
                    "backupCount": 3,
                    "encoding": "utf-8",
                    "level": "DEBUG",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
            },
        }
    )
