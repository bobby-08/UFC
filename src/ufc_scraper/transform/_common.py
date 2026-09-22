"""Shared configuration, schema, staging readers, and writers for transforms."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tomllib

import polars as pl

from ..config import CONFIG_ROOT, PATHS, PROJECT_ROOT
from ..logging import get_logger


LOGGER = get_logger(__name__, stage="transform")


def schema_values(filename: str) -> dict:
    with (CONFIG_ROOT.parent / "schemas" / filename).open("rb") as handle:
        return tomllib.load(handle)


def staging_path(name: str) -> Path:
    return PROJECT_ROOT / PATHS["staging"][name]


def transformation_path(name: str) -> Path:
    return PROJECT_ROOT / PATHS["transformation"][name]


def read_staging(name: str, path: str | Path | None = None) -> pl.DataFrame:
    """Read all timestamped staging Parquet files for a configured dataset."""
    source = Path(path) if path is not None else staging_path(name)
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    return pl.read_parquet(str(source))


def write_transformation(
    df: pl.DataFrame,
    name: str,
    transformed_at: datetime | None = None,
) -> Path:
    transformed_at = transformed_at or datetime.now(timezone.utc)
    df = df.with_columns(pl.lit(transformed_at).alias("transformed_at"))
    destination = transformation_path(name)
    if "*" in str(destination):
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        destination = Path(str(destination).replace("*", timestamp, 1))
    destination.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(destination)
    LOGGER.info("Wrote transformed dataset=%s rows=%d path=%s", name, df.height, destination)
    return destination
