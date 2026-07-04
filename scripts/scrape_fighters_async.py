from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper
from ufc_scraper.storage import build_raw_output_path


async def main() -> None:
    scraper = UFCStatsFightersScraper()
    rows = await scraper.scrape_all_fighters_async()
    output_path = build_raw_output_path("fighters", "fighters.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps([asdict(row) for row in rows], indent=2), encoding="utf-8")
    print(f"Found {len(rows)} fighters")
    print(f"Saved to {output_path}")
    for r in rows[:5]:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())
