"""Quality rules for transformed Parquet datasets.

The rules here are intentionally close to the processed data contract. They
are run before loading DuckDB so schema drift or bad keys cannot silently enter
the database.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from glob import glob

import polars as pl

from ..config import PATHS, PROJECT_ROOT
from ..logging import get_logger


LOGGER = get_logger(__name__, stage="pipeline")


@dataclass(frozen=True)
class DatasetSpec:
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]


PROCESSED_DATASET_SPECS = {
    "events": DatasetSpec(
        columns=("event_id", "event_name", "event_date", "event_location", "scraped_at", "ingested_at", "transformed_at"),
        primary_key=("event_id",),
    ),
    "fighters": DatasetSpec(
        columns=("fighter_id", "fighter_name", "nickname", "height_inches", "weight_lbs", "reach_inches", "stance", "scraped_at", "ingested_at", "transformed_at"),
        primary_key=("fighter_id",),
    ),
    "fighter_stats": DatasetSpec(
        columns=("fighter_id", "wins", "losses", "draws", "belt", "scraped_at", "ingested_at", "transformed_at"),
        primary_key=("fighter_id",),
    ),
    "fight_summary": DatasetSpec(
        columns=("fight_id", "event_id", "event_name", "bout_type", "method", "round", "time", "time_seconds", "time_format", "referee", "details", "scraped_at", "ingested_at", "winner", "loser", "fighter", "opponent", "fighter_result", "nickname", "transformed_at"),
        primary_key=("fight_id", "fighter"),
    ),
    "totals": DatasetSpec(
        columns=("fight_id", "event_id", "round", "scraped_at", "ingested_at", "fighter", "opponent", "sig_str_landed", "sig_str_attempted", "total_str_landed", "total_str_attempted", "td_landed", "td_attempted", "sig_str_pct", "td_pct", "total_str_pct", "kd", "sub_att", "rev", "ctrl_seconds", "transformed_at"),
        primary_key=("fight_id", "round", "fighter"),
    ),
    "significant_strikes": DatasetSpec(
        columns=("fight_id", "event_id", "round", "scraped_at", "ingested_at", "fighter", "opponent", "sig_str_landed", "sig_str_attempted", "sig_str_pct", "head_landed", "head_attempted", "head_pct", "body_landed", "body_attempted", "body_pct", "leg_landed", "leg_attempted", "leg_pct", "distance_landed", "distance_attempted", "distance_pct", "clinch_landed", "clinch_attempted", "clinch_pct", "ground_landed", "ground_attempted", "ground_pct", "transformed_at"),
        primary_key=("fight_id", "round", "fighter"),
    ),
}


class DataQualityError(ValueError):
    """Raised when processed data violates the load contract."""


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deduplicate_processed_files(files: dict[str, list[Path]]) -> dict[str, list[Path]]:
    """Remove byte-identical rerun files while retaining timestamp order.

    Different runs with changed timestamps are retained and loaded in sorted
    order; DuckDB's primary-key replacement then makes the latest run win.
    """
    result: dict[str, list[Path]] = {}
    for dataset, paths in files.items():
        seen: dict[str, Path] = {}
        unique: list[Path] = []
        for path in paths:
            checksum = _checksum(path)
            if checksum in seen:
                LOGGER.warning(
                    "Duplicate processed run detected dataset=%s path=%s duplicate_of=%s action=skip",
                    dataset,
                    path,
                    seen[checksum],
                )
                continue
            seen[checksum] = path
            unique.append(path)
        result[dataset] = unique
    return result


def check_processed_files(files: dict[str, list[Path]]) -> dict[str, int]:
    """Validate schema, keys, row counts, and null rates for processed files."""
    errors: list[str] = []
    row_counts: dict[str, int] = {}
    for dataset, paths in files.items():
        spec = PROCESSED_DATASET_SPECS[dataset]
        total_rows = 0
        seen_keys: set[tuple[object, ...]] = set()
        for path in paths:
            frame = pl.read_parquet(path)
            total_rows += frame.height
            missing = sorted(set(spec.columns) - set(frame.columns))
            unexpected = sorted(set(frame.columns) - set(spec.columns))
            if missing or unexpected:
                errors.append(f"{dataset}: {path} schema mismatch missing={missing} unexpected={unexpected}")
                continue
            if frame.height == 0:
                errors.append(f"{dataset}: {path} contains zero rows")
                continue

            null_rates = {
                column: frame.get_column(column).null_count() / frame.height
                for column in spec.columns
                if frame.get_column(column).null_count()
            }
            for column, rate in null_rates.items():
                if rate >= 0.5:
                    LOGGER.warning("High null rate dataset=%s column=%s rate=%.3f path=%s", dataset, column, rate, path)

            key_frame = frame.select(spec.primary_key)
            for row in key_frame.iter_rows():
                if any(value is None for value in row):
                    errors.append(f"{dataset}: {path} contains null primary-key value key={spec.primary_key}")
                    break
                key = tuple(row)
                if key in seen_keys:
                    LOGGER.warning("Repeated logical key across processed runs dataset=%s key=%s action=latest_run_wins", dataset, key)
                seen_keys.add(key)
            duplicate_count = frame.height - key_frame.unique().height
            if duplicate_count:
                errors.append(f"{dataset}: {path} contains {duplicate_count} duplicate primary-key rows")

            LOGGER.info("Processed quality dataset=%s path=%s rows=%d null_columns=%d", dataset, path, frame.height, len(null_rates))
        if total_rows == 0:
            errors.append(f"{dataset}: no rows found across processed files")
        row_counts[dataset] = total_rows

    if errors:
        raise DataQualityError("Processed data quality checks failed: " + "; ".join(errors))
    return row_counts


def check_stage_comparisons(files: dict[str, list[Path]]) -> None:
    """Compare processed row counts and shared-column null rates with staging.

    Fighter-level views intentionally expand each source fight row into two
    fighter rows, so those datasets use an expansion factor of two.
    """
    comparisons = {
        "events": ("events", 1),
        "fighters": ("fighters", 1),
        "fighter_stats": ("fighters", 1),
        "fight_summary": ("fight_summary", 2),
        "totals": ("totals", 2),
        "significant_strikes": ("significant_strikes", 2),
    }
    for dataset, (staging_name, expansion_factor) in comparisons.items():
        staging_pattern = PROJECT_ROOT / PATHS["staging"][staging_name]
        staging_paths = [Path(path) for path in glob(str(staging_pattern))]
        if not staging_paths:
            raise DataQualityError(f"No staging files found for comparison dataset={staging_name}")
        staging = pl.read_parquet(staging_paths)
        staging_rows = staging.height
        for processed_path in files[dataset]:
            processed = pl.read_parquet(processed_path)
            expected_rows = staging_rows * expansion_factor
            if processed.height != expected_rows:
                raise DataQualityError(
                    f"Row-count mismatch dataset={dataset} processed={processed_path} "
                    f"rows={processed.height} expected_from_staging={expected_rows}"
                )

            shared_columns = sorted(set(staging.columns) & set(processed.columns))
            for column in shared_columns:
                staging_null_rate = staging.get_column(column).null_count() / max(staging.height, 1)
                processed_null_rate = processed.get_column(column).null_count() / max(processed.height, 1)
                if processed_null_rate > staging_null_rate + 0.25:
                    LOGGER.warning(
                        "Null rate increased dataset=%s column=%s staging=%.3f processed=%.3f path=%s",
                        dataset,
                        column,
                        staging_null_rate,
                        processed_null_rate,
                        processed_path,
                    )
            LOGGER.info(
                "Stage comparison dataset=%s staging_rows=%d processed_rows=%d expansion_factor=%d path=%s",
                dataset,
                staging_rows,
                processed.height,
                expansion_factor,
                processed_path,
            )
