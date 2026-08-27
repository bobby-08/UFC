from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.storage import build_raw_output_path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-pipeline", action="store_true", help="Record the run in DuckDB")
    args = parser.parse_args()
    output_path = build_raw_output_path("events", "latest_event.json")
    scraper = UFCStatsEventsScraper()
    latest_event, main_event = asyncio.run(scraper.scrape_latest_event_async())
    payload = {
                "event": {
                    "event_link": latest_event.event_link,
                    "event_name": latest_event.event_name,
                    "event_date": latest_event.event_date,
                    "event_location": latest_event.event_location,
                },
                "main_event": {
                    "fight_link": main_event.fight_link,
                    "fighter_1": main_event.fighter_1,
                    "fighter_2": main_event.fighter_2,
                    "result_fighter_1": main_event.result_fighter_1,
                    "result_fighter_2": main_event.result_fighter_2,
                    "weight_class": main_event.weight_class,
                    "method": main_event.method,
                    "round": main_event.round,
                    "time": main_event.time,
                },
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.track_pipeline:
        from ufc_scraper.db import create_schema, finish_pipeline_run_success, get_connection, register_pipeline_file, start_pipeline_run
        with get_connection() as connection:
            create_schema(connection)
            run = start_pipeline_run(connection, dataset_name="events")
            register_pipeline_file(connection, run.run_id, "events", output_path)
            finish_pipeline_run_success(connection, run.run_id, output_path=output_path, record_count=1)
    print(json.dumps(payload, indent=2))
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
