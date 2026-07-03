from __future__ import annotations

from dataclasses import dataclass

from .client import UFCStatsClient
from .parser import UFCStatsParser


@dataclass(slots=True)
class FighterRow:
    fighter_id: str
    fighter_link: str
    first_name: str
    last_name: str
    nickname: str
    height: str
    weight: str
    reach: str
    stance: str
    wins: str
    losses: str
    draws: str
    belt: str


class UFCStatsFightersScraper:
    def __init__(self, client: UFCStatsClient | None = None, parser: UFCStatsParser | None = None) -> None:
        self.client = client or UFCStatsClient()
        self.parser = parser or UFCStatsParser()

    def parse_fighter_rows(self, html: str) -> list[FighterRow]:
        soup = self.parser.soup(html)
        table = soup.select_one("table.b-statistics__table")
        if table is None:
            raise ValueError("Could not find the UFC Stats fighters table")

        rows: list[FighterRow] = []
        for row in table.select("tr.b-statistics__table-row"):
            cells = row.find_all("td")
            if len(cells) < 11:
                continue

            links = row.select("a.b-link.b-link_style_black")
            if not links:
                continue

            fighter_link = self.parser.attr(links[0], "href")
            fighter_id = fighter_link.rstrip("/").split("/")[-1]

            rows.append(
                FighterRow(
                    fighter_id=fighter_id,
                    fighter_link=fighter_link,
                    first_name=self.parser.text(cells[0]),
                    last_name=self.parser.text(cells[1]),
                    nickname=self.parser.text(cells[2]),
                    height=self.parser.text(cells[3]),
                    weight=self.parser.text(cells[4]),
                    reach=self.parser.text(cells[5]),
                    stance=self.parser.text(cells[6]),
                    wins=self.parser.text(cells[7]),
                    losses=self.parser.text(cells[8]),
                    draws=self.parser.text(cells[9]),
                    belt=self.parser.text(cells[10]),
                )
            )

        return rows

    def scrape_all_fighters(self) -> list[FighterRow]:
        with self.client as client:
            html = client.get_html("statistics/fighters?page=all")
        return self.parse_fighter_rows(html)

    async def scrape_all_fighters_async(self) -> list[FighterRow]:
        from .client import AsyncUFCStatsClient

        async with AsyncUFCStatsClient() as client:
            html = await client.get_html("statistics/fighters?page=all")

        return self.parse_fighter_rows(html)