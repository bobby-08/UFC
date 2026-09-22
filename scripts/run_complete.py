"""Record the successful end of the Airflow UFC pipeline in the logs."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="pipeline")


def main() -> int:
    completed_at = datetime.now(timezone.utc).isoformat()
    LOGGER.info("UFC pipeline completed successfully completed_at=%s", completed_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
