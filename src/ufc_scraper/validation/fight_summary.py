from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .fight_details import ValidationReport, _add


RESULTS = {"W", "L", "D", "NC"}
SUMMARY_RESULTS = {"", "win", "draw", "no contest"}
ROUND_PATTERN = re.compile(r"^\d+$")
TIME_PATTERN = re.compile(r"^\d+:\d{2}$")


def _valid_url(value: Any, prefix: str) -> bool:
    parsed = urlparse(str(value))
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in {"ufcstats.com", "www.ufcstats.com"} and parsed.path.startswith(prefix)


def _required_text(report: ValidationReport, value: Any, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _add(report, "error", "missing_value", "Value must be a non-empty string", path)


def _optional_text(report: ValidationReport, value: Any, path: str) -> None:
    if not isinstance(value, str):
        _add(report, "error", "invalid_type", "Value must be a string", path)


def validate_fight_summary_payload(payload: Any, file_path: str | Path = "<memory>") -> ValidationReport:
    """Return a validation report for one raw fight-summary payload."""
    report = ValidationReport(str(file_path))
    if not isinstance(payload, Mapping):
        _add(report, "error", "invalid_payload", "Payload must be a JSON object")
        return report

    fields = (
        "fight_link", "event_link", "event_name", "fighter_1", "fighter_1_result",
        "fighter_1_nickname", "fighter_2", "fighter_2_result", "fighter_2_nickname",
        "result", "winner", "loser", "bout_type", "method", "round", "time",
        "time_format", "referee", "details",
    )
    required = {"fight_link", "event_link", "event_name", "fighter_1", "fighter_1_result", "fighter_2", "fighter_2_result", "bout_type", "method", "round", "time", "time_format"}
    missing = sorted(required - payload.keys())
    if missing:
        _add(report, "error", "missing_fields", f"Missing fields: {', '.join(missing)}")
    unexpected = sorted(set(payload) - set(fields))
    if unexpected:
        _add(report, "warning", "unexpected_fields", f"Unexpected fields: {', '.join(unexpected)}")
    for field in fields:
        _required_text(report, payload.get(field), field) if field in required else _optional_text(report, payload.get(field), field)

    if not _valid_url(payload.get("fight_link", ""), "/fight-details/"):
        _add(report, "error", "invalid_fight_url", "Not a UFCStats fight-details URL", "fight_link")
    if not _valid_url(payload.get("event_link", ""), "/event-details/"):
        _add(report, "error", "invalid_event_url", "Not a UFCStats event-details URL", "event_link")

    fighter_1 = str(payload.get("fighter_1", "")).strip()
    fighter_2 = str(payload.get("fighter_2", "")).strip()
    if fighter_1 and fighter_1 == fighter_2:
        _add(report, "error", "duplicate_fighters", "The two fighters must be different")

    result_1 = str(payload.get("fighter_1_result", "")).strip().upper()
    result_2 = str(payload.get("fighter_2_result", "")).strip().upper()
    for number, result in ((1, result_1), (2, result_2)):
        if result not in RESULTS:
            _add(report, "error", "invalid_result", f"Invalid fighter result: {result!r}", f"fighter_{number}_result")
    expected = {"W": "L", "L": "W", "D": "D", "NC": "NC"}
    if result_1 in expected and result_2 != expected[result_1]:
        _add(report, "error", "result_mismatch", "Fighter result codes are inconsistent")

    summary_result = str(payload.get("result", "")).strip().lower()
    if summary_result not in SUMMARY_RESULTS:
        _add(report, "error", "invalid_summary_result", f"Invalid summary result: {summary_result!r}", "result")
    expected_summary = {"W": "win", "L": "win", "D": "draw", "NC": "no contest"}
    if result_1 in expected_summary and summary_result != expected_summary[result_1]:
        _add(report, "error", "summary_result_mismatch", "Summary result does not match fighter results", "result")
    winner = str(payload.get("winner", "")).strip()
    loser = str(payload.get("loser", "")).strip()
    if summary_result == "win" and (winner not in {fighter_1, fighter_2} or loser not in {fighter_1, fighter_2} or winner == loser):
        _add(report, "error", "winner_loser_mismatch", "Winner and loser must be the two opposing fighters")
    if summary_result != "win" and (winner or loser):
        _add(report, "error", "unexpected_winner_loser", "Winner and loser must be empty for a draw or no contest")

    round_value = str(payload.get("round", "")).strip()
    if round_value and not ROUND_PATTERN.fullmatch(round_value):
        _add(report, "error", "invalid_round", "Round must be an integer string", "round")
    time_value = str(payload.get("time", "")).strip()
    if time_value and not TIME_PATTERN.fullmatch(time_value):
        _add(report, "error", "invalid_time", "Time must use M:SS format", "time")
    report.totals_rows = 1
    return report


def validate_fight_summary_file(path: str | Path) -> ValidationReport:
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
    return validate_fight_summary_payload(payload, file_path)


__all__ = ["validate_fight_summary_file", "validate_fight_summary_payload"]
