from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.db import (
    event_is_already_downloaded,
    ensure_pipeline_audit_tables,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    parse_event_date,
    register_downloaded_event,
    register_pipeline_file,
    start_pipeline_run,
)
from ufc_scraper.logging import get_logger
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


LOGGER = get_logger(__name__, stage="scrape")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-pipeline", action="store_true", help="Record the run in DuckDB")
    parser.add_argument("--event-url", help="Extract this specific event instead of the latest event")
    args = parser.parse_args()
    scraper = UFCStatsEventsScraper()
    if args.event_url:
        latest_event = asyncio.run(scraper.scrape_event_only_async(args.event_url))
    else:
        latest_event = asyncio.run(scraper.get_latest_event_async())

    event_id = url_identifier(latest_event.event_link, "/event-details/")
    if not event_id:
        raise ValueError(f"Could not derive an event ID from URL: {latest_event.event_link}")
    event_date = parse_event_date(latest_event.event_date)

    if args.track_pipeline:
        with get_connection() as connection:
            ensure_pipeline_audit_tables(connection)
            if event_is_already_downloaded(connection, event_id, event_date):
                LOGGER.info(
                    "Skipping already-covered event event_id=%s event_date=%s",
                    event_id,
                    event_date,
                )
                return

            run = start_pipeline_run(
                connection,
                dataset_name="events",
                source_url=latest_event.event_link,
            )
            try:
                latest_event, _main_event = asyncio.run(
                    scraper.scrape_event_async(latest_event.event_link)
                )
                output_path = build_raw_output_path("events", "latest_event.json")
                payload = {
                    "event": {
                        "event_link": latest_event.event_link,
                        "event_name": latest_event.event_name,
                        "event_date": latest_event.event_date,
                        "event_location": latest_event.event_location,
                    },
                    "scraped_at": scraped_timestamp(),
                    "event_id": event_id,
                }
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                register_pipeline_file(connection, run.run_id, "events", output_path)
                register_downloaded_event(
                    connection,
                    event_id=event_id,
                    event_link=latest_event.event_link,
                    event_name=latest_event.event_name,
                    event_date=event_date,
                    file_path=output_path,
                )
                finish_pipeline_run_success(connection, run.run_id, output_path=output_path, record_count=1)
            except Exception as exc:
                finish_pipeline_run_failure(connection, run.run_id, exc)
                raise
    else:
        latest_event, _main_event = asyncio.run(scraper.scrape_event_async(latest_event.event_link))
        output_path = build_raw_output_path("events", "latest_event.json")
        payload = {
            "event": {
                "event_link": latest_event.event_link,
                "event_name": latest_event.event_name,
                "event_date": latest_event.event_date,
                "event_location": latest_event.event_location,
            },
            "scraped_at": scraped_timestamp(),
            "event_id": event_id,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    LOGGER.info("Saved latest event path=%s event_id=%s", output_path, payload["event_id"])
    LOGGER.debug("Scraped event payload=%s", payload)


if __name__ == "__main__":
    main()
