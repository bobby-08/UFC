from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.logging import get_logger
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


LOGGER = get_logger(__name__, stage="scrape")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-pipeline", action="store_true", help="Record the run in DuckDB")
    parser.add_argument("--event-url", help="Extract this specific event instead of the latest event")
    args = parser.parse_args()
    output_path = build_raw_output_path("events", "latest_event.json")
    scraper = UFCStatsEventsScraper()
    if args.event_url:
        latest_event = asyncio.run(scraper.scrape_event_only_async(args.event_url))
    else:
        latest_event, main_event = asyncio.run(scraper.scrape_latest_event_async())
    payload = {
                "event": {
                    "event_link": latest_event.event_link,
                    "event_name": latest_event.event_name,
                    "event_date": latest_event.event_date,
                    "event_location": latest_event.event_location,
                },
    }
    payload["scraped_at"] = scraped_timestamp()
    payload["event_id"] = url_identifier(latest_event.event_link, "/event-details/")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.track_pipeline:
        from ufc_scraper.db import create_schema, finish_pipeline_run_success, get_connection, register_pipeline_file, start_pipeline_run
        with get_connection() as connection:
            create_schema(connection)
            run = start_pipeline_run(connection, dataset_name="events")
            register_pipeline_file(connection, run.run_id, "events", output_path)
            finish_pipeline_run_success(connection, run.run_id, output_path=output_path, record_count=1)
    LOGGER.info("Saved latest event path=%s event_id=%s", output_path, payload["event_id"])
    LOGGER.debug("Scraped event payload=%s", payload)


if __name__ == "__main__":
    main()
