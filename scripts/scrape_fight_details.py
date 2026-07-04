from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.scrapers.fights_details import UFCStatsFightsDetailsScraper, build_fight_details_payload
from ufc_scraper.storage import build_raw_output_path


def default_output_path(fight_url: str) -> Path:
    fight_id = Path(urlparse(fight_url).path).name
    if not fight_id:
        fight_id = "fight_details"
    return build_raw_output_path("fight_details", f"fight_details_{fight_id}.json")


def write_json_payload(totals, sigs, fight_url: str, output_path: Path) -> tuple[int, int]:
    payload = build_fight_details_payload(fight_url, totals, sigs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(payload["totals"]), len(payload["significant_strikes"])


def write_json_from_html(html: str, fight_url: str, output_path: Path) -> tuple[int, int]:
    scraper = UFCStatsFightsDetailsScraper()
    totals = scraper.parse_totals(html, fight_url=fight_url)
    sigs = scraper.parse_significant_strikes(html, fight_url=fight_url)
    return write_json_payload(totals, sigs, fight_url, output_path)


async def write_json_from_url_async(fight_url: str, output_path: Path) -> tuple[int, int]:
    scraper = UFCStatsFightsDetailsScraper()
    totals, sigs = await scraper.scrape_fight_details_async(fight_url)
    return write_json_payload(totals, sigs, fight_url, output_path)


async def write_json_from_latest_event_async(output_path: Path) -> tuple[int, int]:
    events_scraper = UFCStatsEventsScraper()
    latest_event, fight_row = await events_scraper.scrape_latest_event_async()

    fight_url = fight_row.fight_link
    if not fight_url:
        raise RuntimeError(f"Could not determine fight URL for latest event: {latest_event.event_name}")

    return await write_json_from_url_async(fight_url, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export UFCStats fight-details rows to JSON")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--latest-event", action="store_true", help="Fetch the latest event's top fight")
    source.add_argument("--url", help="Fight-details page URL")
    source.add_argument("--html", type=Path, help="Saved fight-details HTML file")
    parser.add_argument("--fight-url", help="Fight URL to write into the output when parsing HTML")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv if argv is not None else sys.argv[1:]))

    if args.latest_event:
        output_path = args.output or build_raw_output_path("fight_details", "latest_event_fight_details.json")
        totals_count, sig_count = asyncio.run(write_json_from_latest_event_async(output_path))
        fight_url = "latest event fight"
    elif args.url:
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
