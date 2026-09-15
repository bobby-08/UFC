from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import project_path


RAW_ROOT = project_path("raw", "root")


def build_timestamp_folder_name(now: datetime | None = None) -> str:
    """Return a filesystem-safe timestamp folder name."""
    current = now or datetime.now()
    return current.strftime("%Y-%m-%dT%H-%M-%S")


def build_raw_output_path(category: str, filename: str, now: datetime | None = None) -> Path:
    """Build a timestamped raw output path for a scraped dataset."""
    timestamp = build_timestamp_folder_name(now)
    return RAW_ROOT / category / timestamp / filename
