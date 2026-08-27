from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STAGING_ROOT = ROOT / "data" / "staging"


def build_staging_timestamp_folder_name(now: datetime | None = None) -> str:
    """Return a filesystem-safe staging timestamp folder name."""
    current = now or datetime.now()
    return current.strftime("%Y-%m-%dT%H-%M-%S")


def build_staging_output_path(category: str, filename: str, now: datetime | None = None) -> Path:
    """Build a timestamped staging output path for a transformed dataset."""
    timestamp = build_staging_timestamp_folder_name(now)
    return STAGING_ROOT / category / timestamp / filename
