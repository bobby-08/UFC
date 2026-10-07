"""Make sure raw fighter JSON is available for validation and staging.

Reuse the newest archived roster when possible. A full fighter scrape is only
needed when this is a fresh deployment with no raw or archived fighter data.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.config import project_path


LOGGER = logging.getLogger("ufc.ensure_fighters")


def main() -> int:
    raw_root = project_path("raw", "fighters")
    archived_root = project_path("archive", "raw") / "fighters"

    if raw_root.exists() and any(raw_root.rglob("*.json")):
        LOGGER.info("Raw fighter JSON already exists path=%s", raw_root)
        return 0

    archived_files = list(archived_root.rglob("*.json")) if archived_root.exists() else []
    if archived_files:
        # Timestamp folders sort lexically in chronological order. Resolve by
        # timestamp-folder path, choosing the newest archived snapshot.
        source = max(archived_files, key=lambda path: path.relative_to(archived_root).as_posix())
        destination = raw_root / source.relative_to(archived_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        LOGGER.info("Restored archived fighter JSON source=%s destination=%s", source, destination)
        return 0

    LOGGER.info("No raw or archived fighter JSON found; scraping the roster")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scrape_fighters.py"), "--track-pipeline"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    raise SystemExit(main())
