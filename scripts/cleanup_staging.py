"""Remove staging Parquet files after processed-data quality checks pass."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.config import project_path
from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="staging")


def main() -> int:
    staging_root = project_path("staging", "root").resolve()
    if not staging_root.exists():
        LOGGER.info("Staging directory does not exist; nothing to delete path=%s", staging_root)
        return 0

    files = [path for path in staging_root.rglob("*.parquet") if path.is_file()]
    deleted = 0
    for path in files:
        resolved = path.resolve()
        if staging_root not in resolved.parents:
            raise RuntimeError(f"Refusing to delete a path outside staging root: {resolved}")
        path.unlink()
        deleted += 1
        LOGGER.info("Deleted staging file path=%s", path)

    # Remove only empty timestamp/category directories; data/staging itself is kept.
    for directory in sorted(
        (path for path in staging_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if directory != staging_root and not any(directory.iterdir()):
            directory.rmdir()

    LOGGER.info("Staging cleanup completed files_deleted=%d root=%s", deleted, staging_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
