from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.config import project_path
from ufc_scraper.db import (
    ensure_pipeline_audit_tables,
    event_dataset_is_complete,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    mark_event_dataset_complete,
    register_downloaded_resource,
    register_pipeline_file,
    resource_is_downloaded,
    start_pipeline_run,
)
from ufc_scraper.logging import get_logger
from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.scrapers.fights_details import UFCStatsFightsDetailsScraper, build_fight_details_payload
from ufc_scraper.scrapers.fights_summary import UFCStatsFightSummaryScraper
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


LOGGER = get_logger(__name__, stage="scrape")


async def scrape_event(
    event_url: str,
    connection=None,
    run_id: str | None = None,
    run_timestamp: datetime | None = None,
) -> tuple[int, int]:
    """Scrape fight summaries and details for one event with checkpointing."""

    event_id = url_identifier(event_url, "/event-details/")
    if not event_id:
        raise ValueError(f"Could not derive event ID from URL: {event_url}")

    if connection is not None and all(
        event_dataset_is_complete(connection, event_id, dataset)
        for dataset in ("fight_summary", "fight_details")
    ):
        LOGGER.info("Skipping completed event event_id=%s", event_id)
        return 0, 0

    event_scraper = UFCStatsEventsScraper()
    fight_urls = await event_scraper.scrape_event_fight_links_async(event_url)
    LOGGER.info("Found fights=%d event_url=%s", len(fight_urls), event_url)

    summary_count = 0
    details_count = 0
    output_timestamp = run_timestamp or datetime.now(timezone.utc)

    for index, fight_url in enumerate(fight_urls, start=1):
        fight_id = url_identifier(fight_url, "/fight-details/")
        if not fight_id:
            raise ValueError(f"Could not derive fight ID from URL: {fight_url}")

        summary_needed = connection is None or not resource_is_downloaded(
            connection, "fight_summary", fight_id
        )
        details_needed = connection is None or not resource_is_downloaded(
            connection, "fight_details", fight_id
        )
        if not summary_needed and not details_needed:
            LOGGER.info("Skipping downloaded fight_id=%s", fight_id)
            continue

        LOGGER.info("Scraping fight index=%d total=%d fight_url=%s", index, len(fight_urls), fight_url)

        if summary_needed:
            summary = await UFCStatsFightSummaryScraper().scrape_fight_summary_async(fight_url)
            if summary.event_link.rstrip("/") != event_url.rstrip("/"):
                raise RuntimeError(f"Fight {fight_url} does not belong to event {event_url}")
            summary_path = build_raw_output_path(
                "fight_summary", f"fight_summary_{fight_id}.json", now=output_timestamp
            )
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_payload = asdict(summary)
            summary_payload["scraped_at"] = scraped_timestamp()
            summary_payload["event_id"] = event_id
            summary_payload["fight_id"] = fight_id
            summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
            if connection is not None and run_id is not None:
                register_pipeline_file(connection, run_id, "fight_summary", summary_path)
                register_downloaded_resource(connection, "fight_summary", fight_id, summary_path, event_id)
            summary_count += 1
            LOGGER.info("Saved fight summary path=%s", summary_path)

        if details_needed:
            details_scraper = UFCStatsFightsDetailsScraper()
            totals, sigs = await details_scraper.scrape_fight_details_async(fight_url)
            if details_scraper.event_link.rstrip("/") != event_url.rstrip("/"):
                raise RuntimeError(f"Fight {fight_url} details page belongs to {event_url}")
            details_path = build_raw_output_path(
                "fight_details", f"fight_details_{fight_id}.json", now=output_timestamp
            )
            details_path.parent.mkdir(parents=True, exist_ok=True)
            details_payload = build_fight_details_payload(fight_url, totals, sigs, event_url=event_url)
            details_payload["scraped_at"] = scraped_timestamp()
            details_payload["event_id"] = event_id
            details_payload["fight_id"] = fight_id
            details_path.write_text(json.dumps(details_payload, indent=2), encoding="utf-8")
            if connection is not None and run_id is not None:
                register_pipeline_file(connection, run_id, "fight_details", details_path)
                register_downloaded_resource(connection, "fight_details", fight_id, details_path, event_id)
            details_count += 1
            LOGGER.info("Saved fight details path=%s", details_path)

    if connection is not None:
        mark_event_dataset_complete(connection, event_id, "fight_summary", len(fight_urls))
        mark_event_dataset_complete(connection, event_id, "fight_details", len(fight_urls))

    return summary_count, details_count


def _event_urls_from_raw_files() -> list[str]:
    roots = [
        project_path("raw", "events"),
        project_path("archive", "raw") / "events",
    ]
    urls: list[str] = []
    for events_root in roots:
        if not events_root.exists():
            continue
        for path in sorted(events_root.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            event = payload.get("event", {})
            event_url = event.get("event_link")
            if event_url and event_url not in urls:
                urls.append(event_url)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape fight summaries and details for UFCStats events")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event-url", help="Scrape one UFCStats event")
    source.add_argument("--all-events", action="store_true", help="Process raw event files")
    parser.add_argument("--track-pipeline", action="store_true", help="Track files and event status in DuckDB")
    args = parser.parse_args()

    event_urls = [args.event_url] if args.event_url else _event_urls_from_raw_files()
    if not event_urls:
        LOGGER.info("No raw event files found to process")
        return 0

    run_timestamp = datetime.now(timezone.utc)
    if not args.track_pipeline:
        for event_url in event_urls:
            asyncio.run(scrape_event(event_url, run_timestamp=run_timestamp))
        return 0

    with get_connection() as connection:
        ensure_pipeline_audit_tables(connection)
        run = start_pipeline_run(connection, dataset_name="event_fight_data", source_url="raw event files")
        summary_count = 0
        details_count = 0
        try:
            for event_url in event_urls:
                summary_rows, detail_rows = asyncio.run(
                    scrape_event(
                        event_url,
                        connection=connection,
                        run_id=run.run_id,
                        run_timestamp=run_timestamp,
                    )
                )
                summary_count += summary_rows
                details_count += detail_rows
            finish_pipeline_run_success(
                connection,
                run.run_id,
                output_path=ROOT / "data" / "raw",
                record_count=summary_count + details_count,
            )
        except Exception as exc:
            finish_pipeline_run_failure(connection, run.run_id, exc)
            raise

    LOGGER.info(
        "Completed event fight scrape events=%d summaries=%d details=%d",
        len(event_urls),
        summary_count,
        details_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
