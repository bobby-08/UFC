from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.validation import validate_fight_details_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw UFCStats fight-details JSON files")
    parser.add_argument("path", type=Path, nargs="?", help="JSON file or directory; defaults to data/raw/fight_details")
    args = parser.parse_args()
    target = args.path or ROOT / "data" / "raw" / "fight_details"
    files = [target] if target.is_file() else sorted(target.rglob("*.json"))
    if not files:
        print(f"No JSON files found under {target}", file=sys.stderr)
        return 1

    exit_code = 0
    for file_path in files:
        report = validate_fight_details_file(file_path)
        result = "VALID" if report.valid else "INVALID"
        print(f"{result}: {file_path} ({report.totals_rows} totals, {report.significant_strikes_rows} significant-strikes)")
        for issue in report.issues:
            location = f" [{issue.path}]" if issue.path else ""
            print(f"  {issue.severity.upper()} {issue.code}{location}: {issue.message}")
        if not report.valid:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
