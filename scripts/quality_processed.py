"""Run quality checks against processed Parquet and staging outputs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db.load import transformed_files
from ufc_scraper.logging import get_logger
from ufc_scraper.quality import (
    check_processed_files,
    check_stage_comparisons,
    deduplicate_processed_files,
)


LOGGER = get_logger(__name__, stage="pipeline")


def main() -> int:
    LOGGER.info("Starting processed-data quality checks")
    files = deduplicate_processed_files(transformed_files())
    row_counts = check_processed_files(files)
    check_stage_comparisons(files)
    LOGGER.info("Processed-data quality checks passed row_counts=%s", row_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
