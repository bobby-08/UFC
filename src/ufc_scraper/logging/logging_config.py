"""Production-oriented logging configuration for pipeline stages.

Each stage gets one console handler and one timestamped, rotating file handler:
``logs/<stage>/<stage>_<UTC timestamp>.log``.

The following environment variables can be used by scheduled jobs:

* ``UFC_LOG_LEVEL``: default level for files, default ``INFO``
* ``UFC_CONSOLE_LOG_LEVEL``: console level, default ``INFO``
* ``UFC_LOG_DIR``: override the configured logs directory
* ``UFC_LOG_MAX_BYTES``: rotating file size, default 10 MiB
* ``UFC_LOG_BACKUP_COUNT``: rotated file count, default 5
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from threading import Lock

from ..config import project_path


PIPELINE_LOG_STAGES = {
    "scrape",
    "validation",
    "staging",
    "transform",
    "database",
    "pipeline",
}
_CONFIGURED_STAGES: set[str] = set()
_CONFIGURATION_LOCK = Lock()


class UtcFormatter(logging.Formatter):
    """Formatter that writes timestamps in UTC for scheduler-friendly auditing."""

    converter = staticmethod(lambda *args: datetime.now(timezone.utc).timetuple())


def _level(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    resolved = logging.getLevelNamesMapping().get(value.upper())
    if not isinstance(resolved, int):
        raise ValueError(f"Unknown log level: {value!r}")
    return resolved


def _log_root() -> Path:
    configured = os.getenv("UFC_LOG_DIR")
    return Path(configured) if configured else project_path("logs", "root")


def _stage_from_name(name: str) -> str:
    parts = set(name.split("."))
    if "scrapers" in parts:
        return "scrape"
    for stage in ("validation", "staging", "transform", "db"):
        if stage in parts:
            return "database" if stage == "db" else stage
    return "pipeline"


def configure_logging(
    stage: str = "pipeline",
    *,
    level: str | int | None = None,
    console_level: str | int | None = None,
) -> logging.Logger:
    """Configure and return the stage logger.

    Configuration is idempotent within a process. Calling this repeatedly for
    the same stage will not add duplicate handlers.
    """
    if stage not in PIPELINE_LOG_STAGES:
        raise ValueError(f"Unsupported logging stage {stage!r}")

    stage_logger = logging.getLogger(f"ufc_scraper.{stage}")
    stage_logger.setLevel(_level(level or os.getenv("UFC_LOG_LEVEL"), logging.INFO))
    stage_logger.propagate = False

    with _CONFIGURATION_LOCK:
        if stage not in _CONFIGURED_STAGES:
            root = _log_root() / stage
            root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = root / f"{stage}_{timestamp}.log"
            formatter = UtcFormatter(
                fmt="%(asctime)sZ | %(levelname)s | %(name)s | pid=%(process)d | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )

            file_handler = RotatingFileHandler(
                filename,
                maxBytes=int(os.getenv("UFC_LOG_MAX_BYTES", 10 * 1024 * 1024)),
                backupCount=int(os.getenv("UFC_LOG_BACKUP_COUNT", 5)),
                encoding="utf-8",
            )
            file_handler.setLevel(stage_logger.level)
            file_handler.setFormatter(formatter)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(
                _level(console_level or os.getenv("UFC_CONSOLE_LOG_LEVEL"), logging.INFO)
            )
            console_handler.setFormatter(formatter)

            stage_logger.addHandler(file_handler)
            stage_logger.addHandler(console_handler)
            _CONFIGURED_STAGES.add(stage)

    return stage_logger


def get_logger(name: str | None = None, *, stage: str | None = None) -> logging.Logger:
    """Return a configured logger for a module or script.

    Pipeline modules should pass their stage explicitly, for example:
    ``get_logger(__name__, stage="transform")``.
    """
    logger_name = name or "ufc_scraper.pipeline"
    resolved_stage = stage or _stage_from_name(logger_name)
    configure_logging(resolved_stage)
    if logger_name.startswith("ufc_scraper."):
        return logging.getLogger(logger_name)
    return logging.getLogger(f"ufc_scraper.{resolved_stage}.{logger_name}")


def shutdown_logging() -> None:
    """Flush and close all configured handlers."""
    with _CONFIGURATION_LOCK:
        for stage in _CONFIGURED_STAGES:
            logger = logging.getLogger(f"ufc_scraper.{stage}")
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
        _CONFIGURED_STAGES.clear()


__all__ = ["configure_logging", "get_logger", "shutdown_logging"]
