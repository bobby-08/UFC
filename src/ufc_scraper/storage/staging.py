from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import project_path


STAGING_ROOT = project_path("staging", "root")


def build_staging_timestamp_folder_name(now: datetime | None = None) -> str:
    """Return a filesystem-safe staging timestamp folder name."""
    current = now or datetime.now()
    return current.strftime("%Y-%m-%dT%H-%M-%S")


def build_staging_output_path(category: str, filename: str, now: datetime | None = None) -> Path:
    """Build a timestamped staging output path for a transformed dataset."""
    timestamp = build_staging_timestamp_folder_name(now)
    return STAGING_ROOT / category / timestamp / filename
