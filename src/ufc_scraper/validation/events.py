from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .fight_details import ValidationReport, _add


DATE_PATTERNS = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y")
ROUND_PATTERN = re.compile(r"^\d+$")
TIME_PATTERN = re.compile(r"^\d+:\d{2}$")
RESULTS = {"W", "L", "D", "NC"}


def _valid_url(value: Any, path_prefix: str) -> bool:
    parsed = urlparse(str(value))
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.lower() in {"ufcstats.com", "www.ufcstats.com"}
        and parsed.path.startswith(path_prefix)
    )


def _required_text(report: ValidationReport, value: Any, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _add(report, "error", "missing_value", "Value must be a non-empty string", path)


def validate_events_payload(payload: Any, file_path: str | Path = "<memory>") -> ValidationReport:
    """Return a validation report for a raw events/latest-event payload."""
    report = ValidationReport(str(file_path))
    if not isinstance(payload, dict):
        _add(report, "error", "invalid_payload", "Payload must be a JSON object")
        return report

    event = payload.get("event")
    main_event = payload.get("main_event")
    if not isinstance(event, dict):
        _add(report, "error", "missing_section", "event must be an object", "event")
        event = {}
    if isinstance(main_event, dict):
        _add(report, "warning", "legacy_main_event", "main_event is redundant in the event dataset", "main_event")

    for field in ("event_link", "event_name", "event_date", "event_location"):
        _required_text(report, event.get(field), f"event.{field}")
    if not _valid_url(event.get("event_link", ""), "/event-details/"):
        _add(report, "error", "invalid_event_url", "Not a UFCStats event-details URL", "event.event_link")

    event_date = str(event.get("event_date", "")).strip()
    if event_date:
        from datetime import datetime
        if not any(_try_parse_date(event_date, pattern) for pattern in DATE_PATTERNS):
            _add(report, "error", "invalid_event_date", f"Unsupported event date: {event_date!r}", "event.event_date")

    report.totals_rows = 1
    return report


def _try_parse_date(value: str, pattern: str) -> bool:
    from datetime import datetime
    try:
        datetime.strptime(value, pattern)
    except ValueError:
        return False
    return True


def validate_events_file(path: str | Path) -> ValidationReport:
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
    return validate_events_payload(payload, file_path)


__all__ = ["validate_events_file", "validate_events_payload"]
