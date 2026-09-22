"""Polars readers for timestamped staging Parquet files."""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict

import polars as pl

from ..config import project_path


DEFAULT_STAGING_ROOT = project_path("staging", "root")


def _staged_pattern(staging_dir: str | Path, filename: str) -> Path:
    root = Path(staging_dir)
    pattern = root / "*" / filename
    if not any(root.glob(f"*/{filename}")):
        raise FileNotFoundError(f"No {filename} files found under {root}")
    return pattern


def _scan_file_pattern(staging_dir: str | Path, filename: str) -> pl.LazyFrame:
    return pl.scan_parquet(str(_staged_pattern(staging_dir, filename)))


def _scan_files(paths: list[Path]) -> pl.LazyFrame:
    return pl.concat([pl.scan_parquet(str(path)) for path in paths], how="diagonal_relaxed")


def _scan_dataset_file(staging_root: str | Path, dataset: str, filename: str) -> pl.LazyFrame:
    return _scan_file_pattern(Path(staging_root) / dataset, filename)


def read_staged_parquet(
    dataset: str,
    filename: str,
    staging_root: str | Path = DEFAULT_STAGING_ROOT,
) -> pl.LazyFrame:
    """Read any named Parquet file across a dataset's timestamp folders."""
    return _scan_dataset_file(staging_root, dataset, filename)


def read_staged_dataset(
    dataset: str,
    staging_root: str | Path = DEFAULT_STAGING_ROOT,
) -> dict[str, pl.LazyFrame]:
    """Discover every Parquet filename in one timestamped dataset."""
    root = Path(staging_root) / dataset
    paths = sorted(root.glob("*/*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No Parquet files found under {root}")
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        grouped[path.name].append(path)
    return {filename: _scan_files(file_paths) for filename, file_paths in sorted(grouped.items())}


def read_all_staged(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> dict[str, dict[str, pl.LazyFrame]]:
    """Discover every dataset and Parquet file under the staging root."""
    root = Path(staging_root)
    datasets = sorted(path.name for path in root.iterdir() if path.is_dir() and any(path.glob("*/*.parquet")))
    if not datasets:
        raise FileNotFoundError(f"No timestamped Parquet datasets found under {root}")
    return {dataset: read_staged_dataset(dataset, root) for dataset in datasets}


def read_significant_strikes(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read all timestamped significant-strikes Parquet files lazily."""
    return read_staged_parquet("fight_details", "significant_strikes.parquet", staging_root)


def read_totals(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read all timestamped totals Parquet files lazily."""
    return read_staged_parquet("fight_details", "totals.parquet", staging_root)


def read_fight_summary(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read all timestamped fight-summary Parquet files lazily."""
    return _scan_dataset_file(staging_root, "fight_summary", "fight_summary.parquet")


def read_events(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read all timestamped event Parquet files lazily."""
    return _scan_dataset_file(staging_root, "events", "events.parquet")


def read_main_events(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read legacy timestamped main-event Parquet files when present."""
    return _scan_dataset_file(staging_root, "events", "main_events.parquet")


def read_fighters(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> pl.LazyFrame:
    """Read all timestamped fighter Parquet files lazily."""
    return _scan_dataset_file(staging_root, "fighters", "fighters.parquet")


def read_reference_data(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> tuple[pl.LazyFrame, pl.LazyFrame, pl.LazyFrame]:
    """Return ``(fight_summary, events, fighters)`` as separate lazy frames."""
    return read_fight_summary(staging_root), read_events(staging_root), read_fighters(staging_root)

def read_fight_details(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    """Return ``(significant_strikes, totals)`` as separate lazy frames."""
    return read_significant_strikes(staging_root), read_totals(staging_root)


def read_all_fight_details(staging_root: str | Path = DEFAULT_STAGING_ROOT) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Materialize all timestamped fight-detail files as separate DataFrames."""
    significant_strikes, totals = read_fight_details(staging_root)
    return significant_strikes.collect(), totals.collect()


__all__ = [
    "read_all_fight_details", "read_all_staged", "read_events", "read_fight_details", "read_fighters",
    "read_fight_summary", "read_main_events", "read_reference_data",
    "read_significant_strikes", "read_staged_dataset", "read_staged_parquet", "read_totals",
]
