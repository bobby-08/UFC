"""Scrape completed UFCStats events with historical and incremental modes."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db import (
    ensure_pipeline_audit_tables,
    event_is_already_downloaded,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    parse_event_date,
    register_downloaded_event,
    register_pipeline_file,
    start_pipeline_run,
)
from ufc_scraper.logging import get_logger
from ufc_scraper.scrapers.events import EventRow, UFCStatsEventsScraper
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


LOGGER = get_logger(__name__, stage="scrape")


def _event_payload(event: EventRow, event_id: str) -> dict[str, object]:
    return {
        "event": {
            "event_link": event.event_link,
            "event_name": event.event_name,
            "event_date": event.event_date,
            "event_location": event.event_location,
        },
        "scraped_at": scraped_timestamp(),
        "event_id": event_id,
    }


def _write_event(event: EventRow, output_path: Path, event_id: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_event_payload(event, event_id), indent=2),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape completed UFCStats events from the configured date onward"
    )
    parser.add_argument(
        "--backfill-from",
        help="Download all completed events on or after YYYY-MM-DD",
    )
    parser.add_argument(
        "--track-pipeline",
        action="store_true",
        help="Use DuckDB event checkpoints and register downloaded files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backfill_from: date | None = parse_event_date(args.backfill_from) if args.backfill_from else None
    scraper = UFCStatsEventsScraper()
    events = asyncio.run(scraper.get_completed_events_async())
    if not events:
        raise RuntimeError("No completed UFC events were found")

    candidates: list[tuple[EventRow, str, date]] = []
    for event in events:
        event_id = url_identifier(event.event_link, "/event-details/")
        if not event_id:
            LOGGER.warning("Skipping event with invalid URL=%s", event.event_link)
            continue
        event_date = parse_event_date(event.event_date)
        if backfill_from is not None and event_date < backfill_from:
            continue
        candidates.append((event, event_id, event_date))

    if backfill_from is None:
        candidates = candidates[:1]

    run_timestamp = datetime.now(timezone.utc)
    if not args.track_pipeline:
        for event, event_id, _event_date in candidates:
            filename = "latest_event.json" if backfill_from is None else f"event_{event_id}.json"
            output_path = build_raw_output_path("events", filename, now=run_timestamp)
            _write_event(event, output_path, event_id)
            LOGGER.info("Saved event_id=%s event_date=%s path=%s", event_id, event.event_date, output_path)
        return 0

    with get_connection() as connection:
        ensure_pipeline_audit_tables(connection)
        run = start_pipeline_run(
            connection,
            dataset_name="events",
            source_url="http://www.ufcstats.com/statistics/events/completed?page=all",
        )
        downloaded = 0
        try:
            for event, event_id, event_date in candidates:
                if event_is_already_downloaded(
                    connection,
                    event_id,
                    event_date,
                    # A historical backfill must inspect every event from the
                    # requested start date; the latest-event cutoff is only for
                    # incremental runs.
                    use_date_cutoff=backfill_from is None,
                ):
                    LOGGER.info(
                        "Skipping event_id=%s event_date=%s because it is already covered",
                        event_id,
                        event_date,
                    )
                    continue

                filename = "latest_event.json" if backfill_from is None else f"event_{event_id}.json"
                output_path = build_raw_output_path("events", filename, now=run_timestamp)
                _write_event(event, output_path, event_id)
                register_pipeline_file(connection, run.run_id, "events", output_path)
                register_downloaded_event(
                    connection,
                    event_id=event_id,
                    event_link=event.event_link,
                    event_name=event.event_name,
                    event_date=event_date,
                    file_path=output_path,
                )
                downloaded += 1
                LOGGER.info("Saved event_id=%s event_date=%s path=%s", event_id, event_date, output_path)

            finish_pipeline_run_success(
                connection,
                run.run_id,
                output_path=ROOT / "data" / "raw" / "events",
                record_count=downloaded,
            )
        except Exception as exc:
            finish_pipeline_run_failure(connection, run.run_id, exc)
            raise

    LOGGER.info(
        "Completed event scrape mode=%s candidates=%d downloaded=%d",
        "backfill" if backfill_from is not None else "latest",
        len(candidates),
        downloaded,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
