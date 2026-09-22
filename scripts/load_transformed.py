"""Load processed transformation outputs into DuckDB."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db import (
    create_schema,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    load_transformed_data,
    register_pipeline_file,
    start_pipeline_run,
    transformed_files,
)
from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="database")


def main() -> int:
    LOGGER.info("Starting processed-data DuckDB load")
    with get_connection() as connection:
        create_schema(connection)
        run = start_pipeline_run(connection, dataset_name="transformed_data")
        try:
            files = transformed_files()
            for dataset, paths in files.items():
                for path in paths:
                    register_pipeline_file(connection, run.run_id, dataset, path)

            counts = load_transformed_data(connection)
            total_rows = sum(counts.values())
            finish_pipeline_run_success(
                connection,
                run.run_id,
                output_path=ROOT / "data" / "processed",
                record_count=total_rows,
            )
        except Exception as exc:
            finish_pipeline_run_failure(connection, run.run_id, exc)
            LOGGER.exception("Processed-data DuckDB load failed")
            raise

    LOGGER.info("Processed-data DuckDB load completed counts=%s", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
