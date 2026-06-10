from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.fights_details import UFCStatsFightsDetailsScraper


def run_from_file(html_path: Path) -> None:
    html = html_path.read_text(encoding="utf-8")
    scraper = UFCStatsFightsDetailsScraper()
    totals = scraper.parse_totals(html, fight_url=str(html_path))
    sigs = scraper.parse_significant_strikes(html, fight_url=str(html_path))

    print(f"Parsed TOTALS rows: {len(totals)}")
    for r in totals[:10]:
        print(r)

    print(f"Parsed SIGNIFICANT STRIKES rows: {len(sigs)}")
    for r in sigs[:10]:
        print(r)


def fetch_and_run(fight_url: str) -> None:
    scraper = UFCStatsFightsDetailsScraper()
    totals, sigs = scraper.scrape_fight_details(fight_url)

    print(f"Fetched TOTALS rows: {len(totals)}")
    for r in totals[:10]:
        print(r)

    print(f"Fetched SIGNIFICANT STRIKES rows: {len(sigs)}")
    for r in sigs[:10]:
        print(r)


def main(path_or_url: Optional[str] = None) -> None:
    if path_or_url is None:
        print("Usage: python scripts/test_fights_details.py <path-to-html-or-fight-url>")
        return

    p = Path(path_or_url)
    if p.exists():
        run_from_file(p)
    else:
        print("Path doesn't exist; attempting to fetch as URL (requires Playwright and browsers installed).")
        fetch_and_run(path_or_url)


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
