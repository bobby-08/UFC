from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db import (
    create_schema,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    load_fight_details_staging,
    register_pipeline_file,
    start_pipeline_run,
)
from ufc_scraper.transform.not_used_fight_details import stage_fight_details


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and stage UFCStats fight-details JSON")
    parser.add_argument("--load", action="store_true", help="Load the staged Parquet files into DuckDB")
    args = parser.parse_args()
    with get_connection() as connection:
        create_schema(connection)
        run = start_pipeline_run(connection, dataset_name="fight_details_staging")
        try:
            outputs = stage_fight_details()
            for output in outputs.values():
                register_pipeline_file(connection, run.run_id, "fight_details_staging", output)
            loaded = (
                load_fight_details_staging(connection, outputs["totals"], outputs["significant_strikes"])
                if args.load
                else None
            )
            finish_pipeline_run_success(connection, run.run_id, output_path=outputs["totals"].parent, record_count=sum(loaded.values()) if loaded else None)
        except Exception as exc:
            finish_pipeline_run_failure(connection, run.run_id, exc)
            raise
    print(f"Saved totals parquet to {outputs['totals']}")
    print(f"Saved significant strikes parquet to {outputs['significant_strikes']}")
    if loaded:
        print(f"Loaded DuckDB rows: {loaded}")


if __name__ == "__main__":
    main()
