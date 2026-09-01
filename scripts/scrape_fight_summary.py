from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fights_summary import UFCStatsFightSummaryScraper
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


def default_output_path(fight_url: str) -> Path:
    fight_id = Path(urlparse(fight_url).path).name
    if not fight_id:
        fight_id = "fight_summary"
    return build_raw_output_path("fight_summary", f"fight_summary_{fight_id}.json")


async def write_json_from_url_async(fight_url: str, output_path: Path) -> dict[str, str]:
    scraper = UFCStatsFightSummaryScraper()
    row = await scraper.scrape_fight_summary_async(fight_url)

    payload = asdict(row)
    payload["scraped_at"] = scraped_timestamp()
    payload["event_id"] = url_identifier(payload.get("event_link"), "/event-details/")
    payload["fight_id"] = url_identifier(payload.get("fight_link"), "/fight-details/")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export UFCStats fight summary to JSON")
    parser.add_argument("--url", required=True, help="Fight-details page URL")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    parser.add_argument("--track-pipeline", action="store_true", help="Record the run in DuckDB")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv if argv is not None else sys.argv[1:]))

    fight_url = args.url
    output_path = args.output or default_output_path(fight_url)
    if not args.track_pipeline:
        payload = asyncio.run(write_json_from_url_async(fight_url, output_path))
    else:
        from ufc_scraper.db import create_schema, finish_pipeline_run_failure, finish_pipeline_run_success, get_connection, register_pipeline_file, start_pipeline_run
        with get_connection() as connection:
            create_schema(connection)
            run = start_pipeline_run(connection, dataset_name="fight_summary", source_url=fight_url)
            try:
                payload = asyncio.run(write_json_from_url_async(fight_url, output_path))
                register_pipeline_file(connection, run.run_id, "fight_summary", output_path)
                finish_pipeline_run_success(connection, run.run_id, output_path=output_path, record_count=1)
            except Exception as exc:
                finish_pipeline_run_failure(connection, run.run_id, exc, output_path=output_path)
                raise
    print(json.dumps(payload, indent=2))
    print(f"Saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
