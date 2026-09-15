from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.staging import stage_dataset
from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="staging")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw UFCStats JSON and write string-only Parquet staging files")
    parser.add_argument("dataset", choices=("fighters", "events", "fight_summary", "fight_details"))
    args = parser.parse_args()
    LOGGER.info("Starting raw staging dataset=%s", args.dataset)
    outputs = stage_dataset(args.dataset)
    for name, path in outputs.items():
        LOGGER.info("Saved dataset=%s staging_file=%s", name, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
