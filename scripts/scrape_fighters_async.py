from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper


async def main() -> None:
    scraper = UFCStatsFightersScraper()
    rows = await scraper.scrape_all_fighters_async()
    print(f"Found {len(rows)} fighters")
    for r in rows[:5]:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())
