from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class FightDetailsValidationError(ValueError):
    """Raised when a raw UFCStats fight-details payload is invalid."""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    path: str | None = None


@dataclass(slots=True)
class ValidationReport:
    file_path: str
    issues: list[ValidationIssue] = field(default_factory=list)
    totals_rows: int = 0
    significant_strikes_rows: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [x for x in self.issues if x.severity == "error"]

    @property
    def valid(self) -> bool:
        return not self.errors


TOTALS_FIELDS = {
    "round_label", "fighter1", "fighter2", "kd_fighter1", "kd_fighter2",
    "sig_str_fighter1", "sig_str_fighter2", "sig_str_pct_fighter1", "sig_str_pct_fighter2",
    "total_str_fighter1", "total_str_fighter2", "td_fighter1", "td_fighter2",
    "td_pct_fighter1", "td_pct_fighter2", "sub_att_fighter1", "sub_att_fighter2",
    "rev_fighter1", "rev_fighter2", "ctrl_fighter1", "ctrl_fighter2",
}
SIG_FIELDS = {
    "round_label", "fighter1", "fighter2", "sig_str_fighter1", "sig_str_fighter2",
    "sig_str_pct_fighter1", "sig_str_pct_fighter2", "head_fighter1", "head_fighter2",
    "body_fighter1", "body_fighter2", "leg_fighter1", "leg_fighter2",
    "distance_fighter1", "distance_fighter2", "clinch_fighter1", "clinch_fighter2",
    "ground_fighter1", "ground_fighter2",
}
COUNT_PATTERN = re.compile(r"^(?:---|\d+(?:\s+of\s+\d+)?)$")
PERCENT_PATTERN = re.compile(r"^(?:---|\d{1,3}%)$")
TIME_PATTERN = re.compile(r"^(?:---|\d+:\d{2})$")
ROUND_PATTERN = re.compile(r"^(?:Totals|Round \d+)$")


def _add(report: ValidationReport, severity: str, code: str, message: str, path: str | None = None) -> None:
    report.issues.append(ValidationIssue(severity, code, message, path))


def _count(value: Any) -> tuple[int, int] | None:
    text = str(value).strip()
    if text == "---":
        return None
    if " of " in text:
        left, right = text.split(" of ", 1)
        return int(left), int(right)
    number = int(text)
    return number, number


def _check_count(report: ValidationReport, value: Any, path: str) -> tuple[int, int] | None:
    text = str(value).strip()
    if not COUNT_PATTERN.fullmatch(text):
        _add(report, "error", "invalid_count", f"Expected a count or '---', got {value!r}", path)
        return None
    parsed = _count(text)
    if parsed and (parsed[0] < 0 or parsed[1] < 0 or parsed[0] > parsed[1]):
        _add(report, "error", "invalid_count_range", "Landed count exceeds attempted count", path)
        return None
    return parsed


def _section(report: ValidationReport, payload: Mapping[str, Any], name: str, fields: set[str]) -> list[Mapping[str, Any]]:
    rows = payload.get(name)
    if not isinstance(rows, list) or not rows:
        _add(report, "error", "missing_section", f"{name} must be a non-empty list", name)
        return []
    valid_rows: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        path = f"{name}[{index}]"
        if not isinstance(row, Mapping):
            _add(report, "error", "invalid_row", "Row must be a JSON object", path)
            continue
        valid_rows.append(row)
        missing = sorted(fields - row.keys())
        if missing:
            _add(report, "error", "missing_fields", f"Missing fields: {', '.join(missing)}", path)
        unexpected = sorted(set(row) - fields)
        if unexpected:
            _add(report, "warning", "unexpected_fields", f"Unexpected fields: {', '.join(unexpected)}", path)
        round_label = str(row.get("round_label", "")).strip()
        if not ROUND_PATTERN.fullmatch(round_label):
            _add(report, "error", "invalid_round", f"Invalid round label: {round_label!r}", f"{path}.round_label")
        for number in (1, 2):
            if not str(row.get(f"fighter{number}", "")).strip():
                _add(report, "error", "empty_fighter", "Fighter name is empty", f"{path}.fighter{number}")
        for key, value in row.items():
            if key not in fields or key in {"round_label", "fighter1", "fighter2"}:
                continue
            value_text = str(value).strip()
            if "pct" in key:
                if not PERCENT_PATTERN.fullmatch(value_text):
                    _add(report, "error", "invalid_percentage", f"Invalid percentage: {value!r}", f"{path}.{key}")
            elif key.startswith("ctrl_"):
                if not TIME_PATTERN.fullmatch(value_text):
                    _add(report, "error", "invalid_time", f"Invalid control time: {value!r}", f"{path}.{key}")
            else:
                _check_count(report, value, f"{path}.{key}")
    return valid_rows


def _check_duplicates(report: ValidationReport, rows: list[Mapping[str, Any]], section: str) -> None:
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        for number in (1, 2):
            key = (str(row.get("round_label", "")), str(row.get(f"fighter{number}", "")))
            if key in seen:
                _add(report, "error", "duplicate_row", f"Duplicate round/fighter row: {key[0]} / {key[1]}", f"{section}[{index}]")
            seen.add(key)


def validate_fight_details(payload: Any, file_path: str | Path = "<memory>") -> ValidationReport:
    """Return a detailed validation report for one raw payload."""
    report = ValidationReport(str(file_path))
    if not isinstance(payload, Mapping):
        _add(report, "error", "invalid_payload", "Payload must be a JSON object")
        return report
    url = urlparse(str(payload.get("fight_url", "")))
    if url.scheme not in {"http", "https"} or url.netloc.lower() not in {"ufcstats.com", "www.ufcstats.com"} or not url.path.startswith("/fight-details/"):
        _add(report, "error", "invalid_fight_url", "URL is not a UFCStats fight-details URL", "fight_url")
    event_url = payload.get("event_url")
    if not isinstance(event_url, str) or not event_url.strip():
        _add(report, "warning", "missing_event_url", "Parent event URL is missing; it must be resolved from a related summary before staging", "event_url")
    elif not _valid_parent_event_url(event_url):
        _add(report, "error", "invalid_event_url", "Not a UFCStats event-details URL", "event_url")

    totals = _section(report, payload, "totals", TOTALS_FIELDS)
    sigs = _section(report, payload, "significant_strikes", SIG_FIELDS)
    report.totals_rows = len(totals)
    report.significant_strikes_rows = len(sigs)
    _check_duplicates(report, totals, "totals")
    _check_duplicates(report, sigs, "significant_strikes")

    total_keys = {(str(r.get("round_label")), str(r.get(f"fighter{n}"))) for r in totals for n in (1, 2)}
    sig_keys = {(str(r.get("round_label")), str(r.get(f"fighter{n}"))) for r in sigs for n in (1, 2)}
    if total_keys != sig_keys:
        _add(report, "error", "section_mismatch", "Totals and significant-strikes rows do not match")

    sig_by_key = {(str(r.get("round_label")), str(r.get(f"fighter{n}"))): r for r in sigs for n in (1, 2)}
    for index, row in enumerate(totals):
        for n in (1, 2):
            key = (str(row.get("round_label")), str(row.get(f"fighter{n}")))
            sig_row = sig_by_key.get(key)
            if not sig_row:
                continue
            if row.get(f"sig_str_fighter{n}") != sig_row.get(f"sig_str_fighter{n}"):
                _add(report, "error", "stat_mismatch", "sig_str differs between sections", f"totals[{index}]")
            overall = _count(row.get(f"sig_str_fighter{n}", "---"))
            if overall:
                for area in ("head", "body", "leg", "distance", "clinch", "ground"):
                    breakdown = _count(sig_row.get(f"{area}_fighter{n}", "---"))
                    if breakdown and (breakdown[0] > overall[0] or breakdown[1] > overall[1]):
                        _add(report, "error", "breakdown_exceeds_total", f"{area} exceeds sig_str", f"significant_strikes[{index}]")
    return report


def _valid_parent_event_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in {"ufcstats.com", "www.ufcstats.com"} and parsed.path.startswith("/event-details/")


def validate_fight_details_file(path: str | Path) -> ValidationReport:
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
    return validate_fight_details(payload, file_path)


def validate_fight_details_payload(payload: Any, file_path: str | Path = "<memory>") -> dict[str, Any]:
    """Validate and return a raw payload, raising on errors."""
    report = validate_fight_details(payload, file_path)
    if not report.valid:
        raise FightDetailsValidationError("; ".join(issue.message for issue in report.errors))
    return dict(payload)


__all__ = ["FightDetailsValidationError", "ValidationIssue", "ValidationReport", "validate_fight_details", "validate_fight_details_file", "validate_fight_details_payload"]
