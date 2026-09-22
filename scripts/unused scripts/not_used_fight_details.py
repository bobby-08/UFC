"""Transformation entry points for fight details."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..staging.raw_to_parquet import stage_dataset

ROOT = Path(__file__).resolve().parents[3]


def stage_fight_details(
    raw_root: str | Path = ROOT / "data" / "raw" / "fight_details",
    staging_category: str = "fight_details",
    now: datetime | None = None,
) -> dict[str, Path]:
    """Backward-compatible wrapper for the raw fight-details staging step."""
    raw_path = Path(raw_root)
    dataset_root = raw_path.parent if raw_path.name == "fight_details" else raw_path
    if staging_category != "fight_details":
        raise ValueError("staging_category must be 'fight_details'")
    return stage_dataset("fight_details", raw_root=dataset_root, now=now)


__all__ = ["stage_fight_details"]
