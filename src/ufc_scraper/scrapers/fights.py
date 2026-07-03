from __future__ import annotations

from .fights_details import SignificantStrikesRow, TotalsRow, UFCStatsFightsDetailsScraper
from .fights_summary import FightSummaryRow, UFCStatsFightSummaryScraper

FightRoundStats = TotalsRow
UFCStatsFightsScraper = UFCStatsFightSummaryScraper

__all__ = [
    "FightRoundStats",
    "FightSummaryRow",
    "SignificantStrikesRow",
    "TotalsRow",
    "UFCStatsFightSummaryScraper",
    "UFCStatsFightsScraper",
    "UFCStatsFightsDetailsScraper",
]