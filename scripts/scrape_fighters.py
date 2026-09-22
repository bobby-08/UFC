from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper
from ufc_scraper.logging import get_logger
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp


LOGGER = get_logger(__name__, stage="scrape")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-pipeline", action="store_true", help="Record the run in DuckDB")
    args = parser.parse_args()
    LOGGER.info("Starting fighter scrape track_pipeline=%s", args.track_pipeline)
    output_path = build_raw_output_path("fighters", "fighters.json")
    scraper = UFCStatsFightersScraper()
    fighters = asyncio.run(scraper.scrape_all_fighters_async())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scraped_at = scraped_timestamp()
    payload = [
        {**asdict(fighter), "scraped_at": scraped_at}
        for fighter in fighters
    ]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.track_pipeline:
        from ufc_scraper.db import (
            ensure_pipeline_audit_tables,
            finish_pipeline_run_failure,
            finish_pipeline_run_success,
            get_connection,
            register_pipeline_file,
            start_pipeline_run,
        )
        with get_connection() as connection:
            # Scraping must only create/update audit tables; create_schema also
            # recreates transformed tables and must not run during ingestion.
            ensure_pipeline_audit_tables(connection)
            run = start_pipeline_run(connection, dataset_name="fighters")
            try:
                register_pipeline_file(connection, run.run_id, "fighters", output_path)
                finish_pipeline_run_success(
                    connection,
                    run.run_id,
                    output_path=output_path,
                    record_count=len(fighters),
                )
            except Exception as exc:
                finish_pipeline_run_failure(connection, run.run_id, exc)
                raise
    LOGGER.info("Saved fighters=%d path=%s", len(fighters), output_path)
    for fighter in fighters[:5]:
        LOGGER.debug("Sample fighter=%s", asdict(fighter))


if __name__ == "__main__":
    main()
