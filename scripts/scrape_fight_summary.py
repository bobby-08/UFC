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


def default_output_path(fight_url: str) -> Path:
    fight_id = Path(urlparse(fight_url).path).name
    if not fight_id:
        fight_id = "fight_summary"
    return ROOT / "data" / "raw" / f"fight_summary_{fight_id}.json"


async def write_json_from_url_async(fight_url: str, output_path: Path) -> dict[str, str]:
    scraper = UFCStatsFightSummaryScraper()
    row = await scraper.scrape_fight_summary_async(fight_url)

    payload = asdict(row)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export UFCStats fight summary to JSON")
    parser.add_argument("--url", required=True, help="Fight-details page URL")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv if argv is not None else sys.argv[1:]))

    fight_url = args.url
    output_path = args.output or default_output_path(fight_url)

    payload = asyncio.run(write_json_from_url_async(fight_url, output_path))

    print(json.dumps(payload, indent=2))
    print(f"Saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
