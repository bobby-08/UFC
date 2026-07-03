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

from ufc_scraper.scrapers.fights_details import UFCStatsFightsDetailsScraper


def default_output_path(fight_url: str) -> Path:
    fight_id = Path(urlparse(fight_url).path).name
    if not fight_id:
        fight_id = "fight_details"
    return ROOT / "data" / "raw" / f"fight_details_{fight_id}.json"


def write_json_payload(totals, sigs, fight_url: str, output_path: Path) -> None:
    payload = {
        "fight_url": fight_url,
        "totals": [asdict(row) for row in totals],
        "significant_strikes": [asdict(row) for row in sigs],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_json_from_html(html: str, fight_url: str, output_path: Path) -> tuple[int, int]:
    scraper = UFCStatsFightsDetailsScraper()
    totals = scraper.parse_totals(html, fight_url=fight_url)
    sigs = scraper.parse_significant_strikes(html, fight_url=fight_url)
    write_json_payload(totals, sigs, fight_url, output_path)

    return len(totals), len(sigs)


async def write_json_from_url_async(fight_url: str, output_path: Path) -> tuple[int, int]:
    scraper = UFCStatsFightsDetailsScraper()
    totals, sigs = await scraper.scrape_fight_details_async(fight_url)
    write_json_payload(totals, sigs, fight_url, output_path)

    return len(totals), len(sigs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export UFCStats fight-details rows to JSON")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Fight-details page URL")
    source.add_argument("--html", type=Path, help="Saved fight-details HTML file")
    parser.add_argument("--fight-url", help="Fight URL to write into the output when parsing HTML")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv if argv is not None else sys.argv[1:]))

    if args.url:
        fight_url = args.url
        output_path = args.output or default_output_path(fight_url)
        totals_count, sig_count = asyncio.run(write_json_from_url_async(fight_url, output_path))
    else:
        if not args.fight_url:
            parser.error("--fight-url is required when using --html")
        fight_url = args.fight_url
        output_path = args.output or default_output_path(fight_url)
        html = args.html.read_text(encoding="utf-8")
        totals_count, sig_count = write_json_from_html(html, fight_url, output_path)

    print(f"Saved {totals_count + sig_count} rows to {output_path}")
    print(f"Totals rows: {totals_count}")
    print(f"Significant strikes rows: {sig_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
