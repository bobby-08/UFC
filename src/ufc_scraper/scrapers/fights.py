from __future__ import annotations

from dataclasses import dataclass

from .client import UFCStatsClient
from .parser import UFCStatsParser


@dataclass(slots=True)
class FightRoundStats:
    fight_link: str
    round_label: str
    fighter_1: str
    fighter_2: str
    kd_fighter_1: str
    kd_fighter_2: str
    sig_str_fighter_1: str
    sig_str_fighter_2: str
    sig_str_pct_fighter_1: str
    sig_str_pct_fighter_2: str
    total_str_fighter_1: str
    total_str_fighter_2: str
    td_col_1_fighter_1: str
    td_col_1_fighter_2: str
    td_col_2_fighter_1: str
    td_col_2_fighter_2: str
    sub_att_fighter_1: str
    sub_att_fighter_2: str
    rev_fighter_1: str
    rev_fighter_2: str
    ctrl_fighter_1: str
    ctrl_fighter_2: str


class UFCStatsFightsScraper:
    def __init__(self, client: UFCStatsClient | None = None, parser: UFCStatsParser | None = None) -> None:
        self.client = client or UFCStatsClient()
        self.parser = parser or UFCStatsParser()

    def parse_fight_rounds(self, html: str, fight_url: str = "") -> list[FightRoundStats]:
        soup = self.parser.soup(html)
        table = soup.select_one("table.js-fight-table")
        if table is None:
            raise ValueError("Could not find the UFC Stats fight table")

        rounds: list[FightRoundStats] = []
        current_round = ""

        for row in table.select("tr"):
            round_header = row.select_one("th[colspan]")
            if round_header is not None:
                current_round = self.parser.text(round_header)
                continue

            if "b-fight-details__table-row" not in (row.get("class") or []):
                continue

            fighters = self.parser.texts(row.select("td.l-page_align_left a.b-link.b-link_style_black"))
            if len(fighters) < 2:
                continue

            stat_values = self.parser.texts(row.select("td:not(.l-page_align_left) p.b-fight-details__table-text"))
            if len(stat_values) < 18:
                continue

            rounds.append(
                FightRoundStats(
                    fight_link=fight_url,
                    round_label=current_round,
                    fighter_1=fighters[0],
                    fighter_2=fighters[1],
                    kd_fighter_1=stat_values[0],
                    kd_fighter_2=stat_values[1],
                    sig_str_fighter_1=stat_values[2],
                    sig_str_fighter_2=stat_values[3],
                    sig_str_pct_fighter_1=stat_values[4],
                    sig_str_pct_fighter_2=stat_values[5],
                    total_str_fighter_1=stat_values[6],
                    total_str_fighter_2=stat_values[7],
                    td_col_1_fighter_1=stat_values[8],
                    td_col_1_fighter_2=stat_values[9],
                    td_col_2_fighter_1=stat_values[10],
                    td_col_2_fighter_2=stat_values[11],
                    sub_att_fighter_1=stat_values[12],
                    sub_att_fighter_2=stat_values[13],
                    rev_fighter_1=stat_values[14],
                    rev_fighter_2=stat_values[15],
                    ctrl_fighter_1=stat_values[16],
                    ctrl_fighter_2=stat_values[17],
                )
            )

        return rounds

    def scrape_fight(self, fight_url: str) -> list[FightRoundStats]:
        with self.client as client:
            html = client.get_html(fight_url)
        return self.parse_fight_rounds(html, fight_url=fight_url)