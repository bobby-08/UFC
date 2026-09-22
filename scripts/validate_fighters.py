from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.config import project_path
from ufc_scraper.logging import get_logger
from ufc_scraper.validation import validate_fighters_file


LOGGER = get_logger(__name__, stage="validation")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw UFCStats fighter JSON files")
    parser.add_argument("path", type=Path, nargs="?", help="JSON file or directory; defaults to the configured raw fighters path")
    args = parser.parse_args()
    target = args.path or project_path("raw", "fighters")
    files = [target] if target.is_file() else sorted(target.rglob("*.json"))
    if not files:
        LOGGER.error("No JSON files found under path=%s", target)
        return 1
    exit_code = 0
    for file_path in files:
        report = validate_fighters_file(file_path)
        LOGGER.info("Validation result=%s path=%s fighters=%d", "VALID" if report.valid else "INVALID", file_path, report.totals_rows)
        for issue in report.issues:
            location = f" [{issue.path}]" if issue.path else ""
            LOGGER.warning("Validation issue severity=%s code=%s path=%s message=%s", issue.severity, issue.code, location or "<root>", issue.message)
        if not report.valid:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
