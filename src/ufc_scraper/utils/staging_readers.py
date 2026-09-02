"""Polars readers for timestamped staging Parquet files."""

from __future__ import annotations

from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIGHT_DETAILS_STAGING_DIR = ROOT / "data" / "staging" / "fight_details"


def _staged_pattern(staging_dir: str | Path, filename: str) -> Path:
    root = Path(staging_dir)
    pattern = root / "*" / filename
    if not any(root.glob(f"*/{filename}")):
        raise FileNotFoundError(f"No {filename} files found under {root}")
    return pattern


def _scan_file_pattern(staging_dir: str | Path, filename: str) -> pl.LazyFrame:
    return pl.scan_parquet(str(_staged_pattern(staging_dir, filename)))


def read_significant_strikes(staging_dir: str | Path = DEFAULT_FIGHT_DETAILS_STAGING_DIR) -> pl.LazyFrame:
    """Read all timestamped significant-strikes Parquet files lazily."""
    return _scan_file_pattern(staging_dir, "significant_strikes.parquet")


def read_totals(staging_dir: str | Path = DEFAULT_FIGHT_DETAILS_STAGING_DIR) -> pl.LazyFrame:
    """Read all timestamped totals Parquet files lazily."""
    return _scan_file_pattern(staging_dir, "totals.parquet")

def read_fight_details(staging_dir: str | Path = DEFAULT_FIGHT_DETAILS_STAGING_DIR) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    """Return ``(significant_strikes, totals)`` as separate lazy frames."""
    return read_significant_strikes(staging_dir), read_totals(staging_dir)


def read_all_fight_details(staging_dir: str | Path = DEFAULT_FIGHT_DETAILS_STAGING_DIR) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Materialize all timestamped fight-detail files as separate DataFrames."""
    significant_strikes, totals = read_fight_details(staging_dir)
    return significant_strikes.collect(), totals.collect()


__all__ = ["read_all_fight_details", "read_fight_details", "read_significant_strikes", "read_totals"]
