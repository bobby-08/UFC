from __future__ import annotations

from glob import glob
from pathlib import Path

import duckdb

from ..config import PATHS, PROJECT_ROOT
from ..logging import get_logger, timed
from ..quality import check_processed_files, check_stage_comparisons, deduplicate_processed_files


LOGGER = get_logger(__name__, stage="database")

TRANSFORMED_DATASETS = (
    "events",
    "fighters",
    "fighter_stats",
    "fight_summary",
    "totals",
    "significant_strikes",
)


def transformed_files() -> dict[str, list[Path]]:
    """Return all configured processed Parquet files grouped by dataset."""
    result: dict[str, list[Path]] = {}
    for dataset in TRANSFORMED_DATASETS:
        pattern = PROJECT_ROOT / PATHS["transformation"][dataset]
        files = sorted(Path(path) for path in glob(str(pattern)))
        if not files:
            raise FileNotFoundError(f"No transformed Parquet files found for dataset={dataset} pattern={pattern}")
        result[dataset] = files
    return result


@timed(logger=LOGGER)
def load_transformed_data(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, int]:
    """Load every configured processed Parquet dataset into DuckDB.

    Tables are recreated by ``create_transformed_schema`` before this function
    is called, making the load deterministic and independent of staging data.
    """
    files = deduplicate_processed_files(transformed_files())
    check_processed_files(files)
    check_stage_comparisons(files)
    counts: dict[str, int] = {}
    connection.execute("BEGIN")
    try:
        for dataset, paths in files.items():
            pattern = str(PROJECT_ROOT / PATHS["transformation"][dataset])
            count = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [pattern],
            ).fetchone()[0]
            connection.execute(
                f'INSERT OR REPLACE INTO "{dataset}" SELECT * FROM read_parquet(?)',
                [pattern],
            )
            counts[dataset] = count
            LOGGER.info("Loaded transformed dataset=%s files=%d rows=%d", dataset, len(paths), count)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        LOGGER.exception("Failed loading transformed datasets")
        raise
    return counts
