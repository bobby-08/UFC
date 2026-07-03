from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper


def main() -> None:
    output_path = ROOT / "data" / "raw" / "fighters.json"

    scraper = UFCStatsFightersScraper()
    fighters = asyncio.run(scraper.scrape_all_fighters_async())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(fighter) for fighter in fighters]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Saved {len(fighters)} fighters to {output_path}")
    for fighter in fighters[:5]:
        print(asdict(fighter))


if __name__ == "__main__":
    main()
