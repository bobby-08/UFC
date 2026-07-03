from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import List

from .client import AsyncUFCStatsClient, UFCStatsClient
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

    def _normalize_round_label(self, label: str) -> str:
        text = " ".join(label.split())
        lowered = text.lower()
        if "total" in lowered:
            return "Totals"
        match = re.search(r"round\s*(\d+)", text, flags=re.IGNORECASE)
        if match:
            return f"Round {match.group(1)}"
        return text or "Totals"

    def _table_header_text(self, table) -> str:
        header_cells = table.select("thead th, thead td")
        return " ".join(self.parser.texts(header_cells)).upper()

    def _round_labels_from_table(self, table, base_column_count: int) -> List[str]:
        header_cells = table.select("thead th, thead td")
        header_texts = self.parser.texts(header_cells)
        if len(header_texts) <= base_column_count:
            return []
        labels = [self._normalize_round_label(text) for text in header_texts[base_column_count:]]
        return [label for label in labels if label]

    def _is_totals_table(self, table) -> bool:
        header_text = self._table_header_text(table)
        return "KD" in header_text and "TOTAL STR" in header_text

    def _is_significant_strikes_table(self, table) -> bool:
        header_text = self._table_header_text(table)
        return "HEAD" in header_text and "DISTANCE" in header_text and "GROUND" in header_text

    def _iter_stat_tables(self, soup):
        seen_table_ids: set[int] = set()
        for table in soup.select("table.b-fight-details__table.js-fight-table"):
            table_id = id(table)
            if table_id in seen_table_ids:
                continue
            seen_table_ids.add(table_id)
            yield table

    def _extract_fighter_row(self, tr, default_round_label: str = "Totals") -> tuple[str, List[str], List[str], List[str]] | None:
        tds = tr.find_all("td")
        if not tds:
            return None

        fighter_td_index = -1
        fighters: List[str] = []
        for idx, td in enumerate(tds):
            names = [self.parser.text(a) for a in td.select("a.b-link")]
            if len(names) < 2:
                names = self.parser.texts(td.select("p.b-fight-details__table-text"))
            if len(names) >= 2:
                fighter_td_index = idx
                fighters = names[:2]
                break

        if fighter_td_index < 0:
            return None

        row_round_label = default_round_label
        if fighter_td_index > 0:
            candidate = self.parser.text(tds[0])
            row_round_label = self._normalize_round_label(candidate)

        data_tds = tds[fighter_td_index + 1 :]
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

        return row_round_label, fighters, left_vals, right_vals

    def _expand_round_sections_sync(self, page) -> None:
        selectors = [
            "p.b-fight-details__collapse-link_tot",
            "a.b-fight-details__collapse-link",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            for index in range(count):
                try:
                    locator.nth(index).click(timeout=1200)
                    page.wait_for_timeout(150)
                except Exception:
                    continue

    async def _expand_round_sections_async(self, page) -> None:
        selectors = [
            "p.b-fight-details__collapse-link_tot",
            "a.b-fight-details__collapse-link",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            count = await locator.count()
            for index in range(count):
                try:
                    await locator.nth(index).click(timeout=1200)
                    await page.wait_for_timeout(150)
                except Exception:
                    continue

    def parse_totals(self, html: str, fight_url: str = "") -> List[TotalsRow]:
        soup = self.parser.soup(html)
        rows: List[TotalsRow] = []

        for table in self._iter_stat_tables(soup):
            if not self._is_totals_table(table):
                continue
            table_round_labels = self._round_labels_from_table(table, base_column_count=10)

            # The table rows contain two fighters per column (two <p> entries per td)
            for row_index, tr in enumerate(table.select("tbody tr")):
                fallback_round_label = table_round_labels[row_index] if row_index < len(table_round_labels) else "Totals"
                extracted = self._extract_fighter_row(tr, default_round_label=fallback_round_label)
                if extracted is None:
                    continue
                row_round_label, fighters, left_vals, right_vals = extracted

                def make_totals(fighter_name: str, vals: List[str]) -> TotalsRow:
                    return TotalsRow(
                        fight_link=fight_url,
                        round_label=row_round_label,
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

        for table in self._iter_stat_tables(soup):
            if not self._is_significant_strikes_table(table):
                continue
            table_round_labels = self._round_labels_from_table(table, base_column_count=9)

            for row_index, tr in enumerate(table.select("tbody tr")):
                fallback_round_label = table_round_labels[row_index] if row_index < len(table_round_labels) else "Totals"
                extracted = self._extract_fighter_row(tr, default_round_label=fallback_round_label)
                if extracted is None:
                    continue
                row_round_label, fighters, left_vals, right_vals = extracted

                def make_sig(fighter_name: str, vals: List[str]) -> SignificantStrikesRow:
                    return SignificantStrikesRow(
                        fight_link=fight_url,
                        round_label=row_round_label,
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
        return asyncio.run(self.scrape_fight_details_async(fight_url))

    async def scrape_fight_details_async(self, fight_url: str) -> tuple[List[TotalsRow], List[SignificantStrikesRow]]:
        async with AsyncUFCStatsClient(headless=False, persistent_profile=True) as client:
            # Warm the browser session on a normal UFCStats page before the deep-linked fight page.
            try:
                await client.get_html(
                    "",
                    retries=1,
                    retry_delay_seconds=1.5,
                    settle_delay_seconds=0.75,
                )
            except Exception:
                # If the warmup is blocked, continue and let the fight page retry logic decide.
                pass
            html = await client.get_html(
                fight_url,
                required_selector="table.b-fight-details__table.js-fight-table",
                retries=4,
                retry_delay_seconds=3.0,
                settle_delay_seconds=1.25,
            )
            await self._expand_round_sections_async(client.page)
            html = await client.page.content()

        totals = self.parse_totals(html, fight_url=fight_url)
        sigs = self.parse_significant_strikes(html, fight_url=fight_url)
        return totals, sigs


__all__ = ["TotalsRow", "SignificantStrikesRow", "UFCStatsFightsDetailsScraper"]
