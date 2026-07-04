from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re

from .client import AsyncUFCStatsClient, UFCStatsClient
from .parser import UFCStatsParser


@dataclass(slots=True)
class FightSummaryRow:
    fight_link: str
    event_link: str
    event_name: str
    fighter_1: str
    fighter_1_result: str
    fighter_1_nickname: str
    fighter_2: str
    fighter_2_result: str
    fighter_2_nickname: str
    result: str
    winner: str
    loser: str
    bout_type: str
    method: str
    round: str
    time: str
    time_format: str
    referee: str
    details: str


class UFCStatsFightSummaryScraper:
    def __init__(self, client: UFCStatsClient | None = None, parser: UFCStatsParser | None = None) -> None:
        self.client = client or UFCStatsClient()
        self.parser = parser or UFCStatsParser()

    def _normalize_result(self, result: str) -> str:
        normalized = result.strip().upper()
        if normalized in {"W", "L", "D", "NC"}:
            return normalized
        return normalized

    def _parse_result(self, fighter_1: str, fighter_2: str, status_1: str, status_2: str, method: str) -> tuple[str, str, str]:
        method_lower = method.lower()
        status_1 = self._normalize_result(status_1)
        status_2 = self._normalize_result(status_2)

        if "no contest" in method_lower or "NC" in {status_1, status_2}:
            return "no contest", "", ""

        if status_1 == "D" or status_2 == "D":
            return "draw", "", ""

        if status_1 == "W" and status_2 == "L":
            return "win", fighter_1, fighter_2

        if status_1 == "L" and status_2 == "W":
            return "win", fighter_2, fighter_1

        return "", "", ""

    def _section_value(self, section_text: str, label: str) -> str:
        pattern = rf"{re.escape(label)}\s*(.*?)(?=\s*(?:Method:|Round:|Time:|Time format:|Referee:|Details:)|$)"
        match = re.search(pattern, section_text, flags=re.IGNORECASE | re.DOTALL)
        if match is None:
            return ""
        return " ".join(match.group(1).split())

    def parse_fight_summary(self, html: str, fight_url: str = "") -> FightSummaryRow:
        soup = self.parser.soup(html)

        title_link = soup.select_one("h2.b-content__title a.b-link")
        if title_link is None:
            raise ValueError("Could not find the UFC Stats fight title")

        person_nodes = soup.select("div.b-fight-details__persons div.b-fight-details__person")
        if len(person_nodes) < 2:
            raise ValueError("Could not find both fight participants")

        people = []
        for person_node in person_nodes[:2]:
            people.append(
                {
                    "name": self.parser.text(person_node.select_one("h3.b-fight-details__person-name a.b-link.b-fight-details__person-link")),
                    "nickname": self.parser.text(person_node.select_one("p.b-fight-details__person-title")),
                    "result": self.parser.text(person_node.select_one("i.b-fight-details__person-status")),
                }
            )

        fight_section = soup.select_one("div.b-fight-details__fight")
        if fight_section is None:
            raise ValueError("Could not find the fight details section")

        bout_type = self.parser.text(fight_section.select_one("i.b-fight-details__fight-title"))
        section_text = self.parser.text(fight_section)
        method = self._section_value(section_text, "Method:")
        round_label = self._section_value(section_text, "Round:")
        time = self._section_value(section_text, "Time:")
        time_format = self._section_value(section_text, "Time format:")
        referee = self._section_value(section_text, "Referee:")
        details = self._section_value(section_text, "Details:")

        result, winner, loser = self._parse_result(
            people[0]["name"],
            people[1]["name"],
            people[0]["result"],
            people[1]["result"],
            method,
        )

        return FightSummaryRow(
            fight_link=fight_url,
            event_link=self.parser.attr(title_link, "href"),
            event_name=self.parser.text(title_link),
            fighter_1=people[0]["name"],
            fighter_1_result=self._normalize_result(people[0]["result"]),
            fighter_1_nickname=people[0]["nickname"],
            fighter_2=people[1]["name"],
            fighter_2_result=self._normalize_result(people[1]["result"]),
            fighter_2_nickname=people[1]["nickname"],
            result=result,
            winner=winner,
            loser=loser,
            bout_type=bout_type,
            method=method,
            round=round_label,
            time=time,
            time_format=time_format,
            referee=referee,
            details=details,
        )

    def scrape_fight_summary(self, fight_url: str) -> FightSummaryRow:
        return asyncio.run(self.scrape_fight_summary_async(fight_url))

    async def scrape_fight_summary_async(self, fight_url: str) -> FightSummaryRow:
        async with AsyncUFCStatsClient() as client:
            html = await client.get_html(fight_url)

        return self.parse_fight_summary(html, fight_url=fight_url)


__all__ = ["FightSummaryRow", "UFCStatsFightSummaryScraper"]
