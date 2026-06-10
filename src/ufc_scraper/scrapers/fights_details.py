from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .client import UFCStatsClient
from .parser import UFCStatsParser


@dataclass(slots=True)
class TotalsRow:
    fight_link: str
    round_label: str
    fighter: str
    kd: str
    sig_str: str
    sig_str_pct: str
    total_str: str
    td: str
    td_pct: str
    sub_att: str
    rev: str
    ctrl: str


@dataclass(slots=True)
class SignificantStrikesRow:
    fight_link: str
    round_label: str
    fighter: str
    sig_str: str
    sig_str_pct: str
    head: str
    body: str
    leg: str
    distance: str
    clinch: str
    ground: str


class UFCStatsFightsDetailsScraper:
    """Scrape the TOTALS and SIGNIFICANT STRIKES sections from a fight-details page.

    Methods return lists of TotalsRow and SignificantStrikesRow for each fighter in each round.
    """

    def __init__(self, client: UFCStatsClient | None = None, parser: UFCStatsParser | None = None) -> None:
        self.client = client or UFCStatsClient(headless=False, persistent_profile=True)
        self.parser = parser or UFCStatsParser()

    def _split_pair(self, values: List[str]) -> tuple[List[str], List[str]]:
        mid = len(values) // 2
        return values[:mid], values[mid:]

    def parse_totals(self, html: str, fight_url: str = "") -> List[TotalsRow]:
        soup = self.parser.soup(html)
        rows: List[TotalsRow] = []

        # Find the Totals collapse link paragraph and its following table
        for p in soup.select("p.b-fight-details__collapse-link_tot"):
            if "tot" not in self.parser.text(p).lower() and "total" not in self.parser.text(p).lower():
                # sometimes same class used for Significant Strikes; check text
                if "totals" not in self.parser.text(p).lower():
                    continue

            table = p.find_next("table")
            if table is None:
                continue

            # The table rows contain two fighters per column (two <p> entries per td)
            for tr in table.select("tbody tr.b-fight-details__table-row"):
                fighter_td = tr.select_one("td.l-page_align_left")
                if fighter_td is None:
                    continue
                fighters = [self.parser.text(a) for a in fighter_td.select("a.b-link_style_black")]
                if len(fighters) < 2:
                    continue

                # collect values from other tds; each td has two p elements
                tds = [td for td in tr.find_all("td")]
                # skip first column (fighter names)
                data_tds = tds[1:]
                # collect lists of values per fighter
                left_vals: List[str] = []
                right_vals: List[str] = []
                for td in data_tds:
                    texts = self.parser.texts(td.select("p.b-fight-details__table-text"))
                    if len(texts) >= 2:
                        left_vals.append(texts[0])
                        right_vals.append(texts[1])
                    elif len(texts) == 1:
                        left_vals.append(texts[0])
                        right_vals.append("")
                    else:
                        left_vals.append("")
                        right_vals.append("")

                def make_totals(fighter_name: str, vals: List[str]) -> TotalsRow:
                    return TotalsRow(
                        fight_link=fight_url,
                        round_label="Totals",
                        fighter=fighter_name,
                        kd=vals[0] if len(vals) > 0 else "",
                        sig_str=vals[1] if len(vals) > 1 else "",
                        sig_str_pct=vals[2] if len(vals) > 2 else "",
                        total_str=vals[3] if len(vals) > 3 else "",
                        td=vals[4] if len(vals) > 4 else "",
                        td_pct=vals[5] if len(vals) > 5 else "",
                        sub_att=vals[6] if len(vals) > 6 else "",
                        rev=vals[7] if len(vals) > 7 else "",
                        ctrl=vals[8] if len(vals) > 8 else "",
                    )

                rows.append(make_totals(fighters[0], left_vals))
                rows.append(make_totals(fighters[1], right_vals))

        return rows

    def parse_significant_strikes(self, html: str, fight_url: str = "") -> List[SignificantStrikesRow]:
        soup = self.parser.soup(html)
        rows: List[SignificantStrikesRow] = []

        # Find the Significant Strikes collapse link paragraph and its following table
        for p in soup.select("p.b-fight-details__collapse-link_tot"):
            if "significant" not in self.parser.text(p).lower():
                continue

            table = p.find_next("table")
            if table is None:
                continue

            for tr in table.select("tbody tr.b-fight-details__table-row"):
                fighter_td = tr.select_one("td.l-page_align_left")
                if fighter_td is None:
                    continue
                fighters = [self.parser.text(a) for a in fighter_td.select("a.b-link_style_black")]
                if len(fighters) < 2:
                    continue

                data_tds = tr.find_all("td")[1:]
                left_vals: List[str] = []
                right_vals: List[str] = []
                for td in data_tds:
                    texts = self.parser.texts(td.select("p.b-fight-details__table-text"))
                    if len(texts) >= 2:
                        left_vals.append(texts[0])
                        right_vals.append(texts[1])
                    elif len(texts) == 1:
                        left_vals.append(texts[0])
                        right_vals.append("")
                    else:
                        left_vals.append("")
                        right_vals.append("")

                def make_sig(fighter_name: str, vals: List[str]) -> SignificantStrikesRow:
                    return SignificantStrikesRow(
                        fight_link=fight_url,
                        round_label="Totals",
                        fighter=fighter_name,
                        sig_str=vals[0] if len(vals) > 0 else "",
                        sig_str_pct=vals[1] if len(vals) > 1 else "",
                        head=vals[2] if len(vals) > 2 else "",
                        body=vals[3] if len(vals) > 3 else "",
                        leg=vals[4] if len(vals) > 4 else "",
                        distance=vals[5] if len(vals) > 5 else "",
                        clinch=vals[6] if len(vals) > 6 else "",
                        ground=vals[7] if len(vals) > 7 else "",
                    )

                rows.append(make_sig(fighters[0], left_vals))
                rows.append(make_sig(fighters[1], right_vals))

        return rows

    def scrape_fight_details(self, fight_url: str) -> tuple[List[TotalsRow], List[SignificantStrikesRow]]:
        with self.client as client:
            # Warm the browser session on a normal UFCStats page before the deep-linked fight page.
            try:
                client.get_html(
                    "",
                    retries=1,
                    retry_delay_seconds=1.5,
                    settle_delay_seconds=0.75,
                )
            except Exception:
                # If the warmup is blocked, continue and let the fight page retry logic decide.
                pass
            html = client.get_html(
                fight_url,
                required_selector="table.b-fight-details__table.js-fight-table",
                retries=4,
                retry_delay_seconds=3.0,
                settle_delay_seconds=1.25,
            )

        totals = self.parse_totals(html, fight_url=fight_url)
        sigs = self.parse_significant_strikes(html, fight_url=fight_url)
        return totals, sigs


__all__ = ["TotalsRow", "SignificantStrikesRow", "UFCStatsFightsDetailsScraper"]
