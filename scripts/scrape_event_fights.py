from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.scrapers.events import UFCStatsEventsScraper
from ufc_scraper.scrapers.fights_details import UFCStatsFightsDetailsScraper
from ufc_scraper.scrapers.fights_summary import UFCStatsFightSummaryScraper
from ufc_scraper.logging import get_logger
from ufc_scraper.storage import build_raw_output_path, scraped_timestamp, url_identifier


LOGGER = get_logger(__name__, stage="scrape")


async def scrape_event(event_url: str) -> None:
    event_scraper = UFCStatsEventsScraper()
    fight_urls = await event_scraper.scrape_event_fight_links_async(event_url)
    LOGGER.info("Found fights=%d event_url=%s", len(fight_urls), event_url)

    for index, fight_url in enumerate(fight_urls, start=1):
        LOGGER.info("Scraping fight index=%d total=%d fight_url=%s", index, len(fight_urls), fight_url)
        summary_scraper = UFCStatsFightSummaryScraper()
        summary = await summary_scraper.scrape_fight_summary_async(fight_url)
        if summary.event_link.rstrip("/") != event_url.rstrip("/"):
            raise RuntimeError(f"Fight {fight_url} does not belong to event {event_url}")
        summary_path = build_raw_output_path("fight_summary", f"fight_summary_{Path(fight_url).name}.json")
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_payload = asdict(summary)
        summary_payload["scraped_at"] = scraped_timestamp()
        summary_payload["event_id"] = url_identifier(event_url, "/event-details/")
        summary_payload["fight_id"] = url_identifier(fight_url, "/fight-details/")
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        details_scraper = UFCStatsFightsDetailsScraper()
        totals, sigs = await details_scraper.scrape_fight_details_async(fight_url)
        if details_scraper.event_link.rstrip("/") != event_url.rstrip("/"):
            raise RuntimeError(f"Fight {fight_url} details page belongs to {details_scraper.event_link}, not {event_url}")
        from ufc_scraper.scrapers.fights_details import build_fight_details_payload
        details_path = build_raw_output_path("fight_details", f"fight_details_{Path(fight_url).name}.json")
        details_path.parent.mkdir(parents=True, exist_ok=True)
        details_payload = build_fight_details_payload(fight_url, totals, sigs, event_url=event_url)
        details_payload["scraped_at"] = scraped_timestamp()
        details_payload["event_id"] = url_identifier(event_url, "/event-details/")
        details_payload["fight_id"] = url_identifier(fight_url, "/fight-details/")
        details_path.write_text(json.dumps(details_payload, indent=2), encoding="utf-8")
        LOGGER.info("Saved fight summary path=%s", summary_path)
        LOGGER.info("Saved fight details path=%s", details_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape every fight from a UFCStats event")
    parser.add_argument("--event-url", required=True, help="UFCStats event-details URL")
    args = parser.parse_args()
    asyncio.run(scrape_event(args.event_url))


if __name__ == "__main__":
    main()
