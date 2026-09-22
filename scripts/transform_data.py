"""Transform all staged UFC datasets into processed Parquet files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.logging import get_logger
from ufc_scraper.transform.events import save_transformed_events
from ufc_scraper.transform.fighters import save_transformed_fighters
from ufc_scraper.transform.significant_strikes import save_transformed_significant_strikes
from ufc_scraper.transform.summary import save_transformed_fight_summary
from ufc_scraper.transform.totals import save_transformed_totals


LOGGER = get_logger(__name__, stage="transform")


def main() -> int:
    LOGGER.info("Starting transformation of staged UFC datasets")

    outputs = {}
    outputs["events"] = save_transformed_events()
    outputs.update(save_transformed_fighters())
    outputs["fight_summary"] = save_transformed_fight_summary()
    outputs["totals"] = save_transformed_totals()
    outputs["significant_strikes"] = save_transformed_significant_strikes()

    for dataset, path in outputs.items():
        LOGGER.info("Transformed dataset=%s path=%s", dataset, path)
    LOGGER.info("Transformation completed datasets=%d", len(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
