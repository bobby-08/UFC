from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .fight_details import ValidationReport, _add


FIELDS = {
    "fighter_id", "fighter_link", "first_name", "last_name", "nickname",
    "height", "weight", "reach", "stance", "wins", "losses", "draws", "belt",
}
RECORD_PATTERN = re.compile(r"^(?:--|---|\d+)$")
MEASUREMENT_PATTERN = re.compile(r"^(?:--|---|.*\d.*)$")


def _valid_fighter_url(value: Any) -> bool:
    parsed = urlparse(str(value))
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.lower() in {"ufcstats.com", "www.ufcstats.com"}
        and parsed.path.startswith("/fighter-details/")
    )


def _text(report: ValidationReport, value: Any, path: str, required: bool = False) -> None:
    if not isinstance(value, str):
        _add(report, "error", "invalid_type", "Value must be a string", path)
    elif required and not value.strip():
        _add(report, "error", "missing_value", "Value must not be empty", path)


def validate_fighters_payload(payload: Any, file_path: str | Path = "<memory>") -> ValidationReport:
    """Return a validation report for a raw list of UFCStats fighter records."""
    report = ValidationReport(str(file_path))
    if not isinstance(payload, list) or not payload:
        _add(report, "error", "invalid_payload", "Payload must be a non-empty list")
        return report

    seen_ids: set[str] = set()
    seen_links: set[str] = set()
    for index, fighter in enumerate(payload):
        path = f"[{index}]"
        if not isinstance(fighter, Mapping):
            _add(report, "error", "invalid_row", "Fighter must be a JSON object", path)
            continue
        missing = sorted(FIELDS - fighter.keys())
        if missing:
            _add(report, "error", "missing_fields", f"Missing fields: {', '.join(missing)}", path)
        unexpected = sorted(set(fighter) - FIELDS)
        if unexpected:
            _add(report, "warning", "unexpected_fields", f"Unexpected fields: {', '.join(unexpected)}", path)

        fighter_id = fighter.get("fighter_id")
        fighter_link = fighter.get("fighter_link")
        _text(report, fighter_id, f"{path}.fighter_id", required=True)
        _text(report, fighter_link, f"{path}.fighter_link", required=True)
        if isinstance(fighter_id, str) and fighter_id.strip():
            if fighter_id in seen_ids:
                _add(report, "error", "duplicate_fighter_id", f"Duplicate fighter_id: {fighter_id}", f"{path}.fighter_id")
            seen_ids.add(fighter_id)
        if isinstance(fighter_link, str) and fighter_link.strip():
            if fighter_link in seen_links:
                _add(report, "error", "duplicate_fighter_link", f"Duplicate fighter_link: {fighter_link}", f"{path}.fighter_link")
            seen_links.add(fighter_link)
            if not _valid_fighter_url(fighter_link):
                _add(report, "error", "invalid_fighter_url", "Not a UFCStats fighter-details URL", f"{path}.fighter_link")
            elif isinstance(fighter_id, str) and fighter_link.rstrip("/").split("/")[-1] != fighter_id:
                _add(report, "error", "fighter_id_mismatch", "fighter_id does not match the URL", path)

        if not str(fighter.get("first_name", "")).strip() and not str(fighter.get("last_name", "")).strip():
            _add(report, "error", "missing_name", "At least one fighter name field is required", path)
        for field in ("first_name", "last_name", "nickname", "stance", "belt"):
            if field in fighter:
                _text(report, fighter[field], f"{path}.{field}")
        for field in ("wins", "losses", "draws"):
            value = fighter.get(field)
            if not isinstance(value, str) or not RECORD_PATTERN.fullmatch(value.strip()):
                _add(report, "error", "invalid_record", f"Invalid {field} value: {value!r}", f"{path}.{field}")
        for field in ("height", "weight", "reach"):
            value = fighter.get(field)
            if not isinstance(value, str) or not MEASUREMENT_PATTERN.fullmatch(value.strip()):
                _add(report, "error", "invalid_measurement", f"Invalid {field} value: {value!r}", f"{path}.{field}")
    report.totals_rows = len(payload)
    return report


def validate_fighters_file(path: str | Path) -> ValidationReport:
    file_path = Path(path)
    if not file_path.is_file():
        report = ValidationReport(str(file_path))
        _add(report, "error", "missing_file", "File does not exist")
        return report
    if file_path.stat().st_size == 0:
        report = ValidationReport(str(file_path))
        _add(report, "error", "empty_file", "File is empty")
        return report
    try:
        with file_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report = ValidationReport(str(file_path))
        _add(report, "error", "invalid_json", str(exc))
        return report
    return validate_fighters_payload(payload, file_path)


__all__ = ["validate_fighters_file", "validate_fighters_payload"]
