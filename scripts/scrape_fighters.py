from __future__ import annotations

import csv
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.config import FIGHTERS_PATH
from ufc_scraper.scrapers.fighters import UFCStatsFightersScraper


def main() -> None:
    output_path = ROOT / "data" / "raw" / "fighters.csv"

    scraper = UFCStatsFightersScraper()
    with scraper.client as client:
        html = client.get_html(FIGHTERS_PATH)
    fighters = scraper.parse_fighter_rows(html)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file_handle:
        fieldnames = list(asdict(fighters[0]).keys()) if fighters else []
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        for fighter in fighters:
            writer.writerow(asdict(fighter))

    print(f"Saved {len(fighters)} fighters to {output_path}")
    for fighter in fighters[:5]:
        print(asdict(fighter))


if __name__ == "__main__":
    main()