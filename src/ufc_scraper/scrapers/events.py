from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .client import AsyncUFCStatsClient, UFCStatsClient
from .config import EVENTS_PATH
from .parser import UFCStatsParser


@dataclass(slots=True)
class EventRow:
    event_link: str
    event_name: str
    event_date: str
    event_location: str


@dataclass(slots=True)
class FightRow:
    fight_link: str
    fighter_1: str
    fighter_2: str
    result_fighter_1: str
    result_fighter_2: str
    weight_class: str
    method: str
    round: str
    time: str


class UFCStatsEventsScraper:
    def __init__(self, client: UFCStatsClient | None = None, parser: UFCStatsParser | None = None) -> None:
        self.client = client or UFCStatsClient()
        self.parser = parser or UFCStatsParser()

    def parse_event_rows(self, html: str) -> list[EventRow]:
        soup = self.parser.soup(html)
        rows: list[EventRow] = []

        for row in soup.select("table.b-statistics__table-events tr.b-statistics__table-row"):
            link = row.select_one("a.b-link.b-link_style_black")
            date_tag = row.select_one("span.b-statistics__date")
            columns = self.parser.texts(row.find_all("td"))
            if link is None or date_tag is None or len(columns) < 2:
                continue

            rows.append(
                EventRow(
                    event_link=self.parser.attr(link, "href"),
                    event_name=self.parser.text(link),
                    event_date=self.parser.text(date_tag),
                    event_location=columns[1],
                )
            )

        return rows

    def parse_main_event(self, html: str) -> FightRow:
        soup = self.parser.soup(html)
        table = soup.select_one("table.js-fight-table")
        if table is None:
            raise ValueError("Could not find the UFC Stats fight table")

        row = table.select_one("tr.b-fight-details__table-row__hover")
        if row is None:
            raise ValueError("Could not find the main event row")

        fighters = self.parser.texts(row.select("td.l-page_align_left a.b-link.b-link_style_black"))
        columns = self.parser.texts(row.find_all("td"))
        if len(fighters) < 2 or len(columns) < 10:
            raise ValueError("Could not extract the main event statistics row")

        result = row.select_one("i.b-flag__text")
        result_fighter_1 = self._result_code(self.parser.text(result))
        result_fighter_2 = self._opposing_result_code(result_fighter_1)

        return FightRow(
            fight_link=self.parser.attr(row, "data-link"),
            fighter_1=fighters[0],
            fighter_2=fighters[1],
            result_fighter_1=result_fighter_1,
            result_fighter_2=result_fighter_2,
            weight_class=columns[6],
            method=columns[7],
            round=columns[8],
            time=columns[9],
        )

    def parse_fight_links(self, html: str) -> list[str]:
        """Extract all fight-detail URLs from an event page."""
        soup = self.parser.soup(html)
        links: list[str] = []
        for row in soup.select("tr.b-fight-details__table-row[data-link]"):
            fight_link = self.parser.attr(row, "data-link")
            if fight_link and fight_link not in links:
                links.append(fight_link)
        return links

    async def scrape_event_fight_links_async(self, event_url: str) -> list[str]:
        async with AsyncUFCStatsClient() as client:
            html = await client.get_html(event_url, required_selector="tr.b-fight-details__table-row")
        links = self.parse_fight_links(html)
        if not links:
            raise RuntimeError(f"No fights were found for event: {event_url}")
        return links

    def _result_code(self, value: str) -> str:
        normalized = value.strip().lower()
        mapping = {
            "w": "W",
            "l": "L",
            "d": "D",
            "nc": "NC",
            "win": "W",
            "loss": "L",
            "draw": "D",
            "no contest": "NC",
        }
        return mapping.get(normalized, value.strip())

    def _opposing_result_code(self, fighter_1_result: str) -> str:
        if fighter_1_result == "W":
            return "L"
        if fighter_1_result == "L":
            return "W"
        if fighter_1_result in {"D", "NC"}:
            return fighter_1_result
        return ""

    def scrape_latest_event(self) -> tuple[EventRow, FightRow]:
        return asyncio.run(self.scrape_latest_event_async())

    async def scrape_latest_event_async(self) -> tuple[EventRow, FightRow]:
        async with AsyncUFCStatsClient() as client:
            completed_events_html = await client.get_html(EVENTS_PATH)
            events = self.parse_event_rows(completed_events_html)
            if not events:
                raise RuntimeError("No completed UFC events were found")

            latest_event = events[0]
            latest_event_html = await client.get_html(latest_event.event_link)
            main_event = self.parse_main_event(latest_event_html)

        return latest_event, main_event

    async def scrape_event_async(self, event_url: str) -> tuple[EventRow, FightRow]:
        """Scrape a specific event and its main-event row."""
        async with AsyncUFCStatsClient() as client:
            completed_events_html = await client.get_html(EVENTS_PATH)
            events = self.parse_event_rows(completed_events_html)
            event = next((item for item in events if item.event_link.rstrip("/") == event_url.rstrip("/")), None)
            if event is None:
                raise ValueError(f"Event URL was not found in the completed-events listing: {event_url}")
            event_html = await client.get_html(event_url)
            main_event = self.parse_main_event(event_html)
        return event, main_event

    async def scrape_event_only_async(self, event_url: str) -> EventRow:
        """Return only the event entity for a specific event URL."""
        async with AsyncUFCStatsClient() as client:
            completed_events_html = await client.get_html(EVENTS_PATH)
        events = self.parse_event_rows(completed_events_html)
        event = next((item for item in events if item.event_link.rstrip("/") == event_url.rstrip("/")), None)
        if event is None:
            raise ValueError(f"Event URL was not found in the completed-events listing: {event_url}")
        return event
