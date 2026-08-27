from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db import (
    create_schema,
    finish_pipeline_run_failure,
    finish_pipeline_run_success,
    get_connection,
    register_pipeline_file,
    start_pipeline_run,
)
from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper
from ufc_scraper.storage import build_raw_output_path


async def main() -> None:
    scraper = UFCStatsFightersScraper()
    rows = await scraper.scrape_all_fighters_async()
    output_path = build_raw_output_path("fighters", "fighters.json")
    with get_connection() as connection:
        create_schema(connection)
        run = start_pipeline_run(connection, dataset_name="fighters")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps([asdict(row) for row in rows], indent=2), encoding="utf-8")
            register_pipeline_file(connection, run.run_id, "fighters", output_path)
            finish_pipeline_run_success(connection, run.run_id, output_path=output_path, record_count=len(rows))
            print(f"Found {len(rows)} fighters")
            print(f"Saved to {output_path}")
            for r in rows[:5]:
                print(r)
        except Exception as exc:
            finish_pipeline_run_failure(connection, run.run_id, exc, output_path=output_path)
            raise


if __name__ == "__main__":
    asyncio.run(main())
