from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from ..storage import build_staging_output_path
from ..storage import scraped_timestamp, url_identifier
from ..validation import (
    validate_events_file,
    validate_fight_details_file,
    validate_fight_summary_file,
    validate_fighters_file,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = ROOT / "data" / "raw"


def _json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _string_frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Create a frame whose complete schema consists of Utf8 columns."""
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).with_columns(pl.all().cast(pl.Utf8, strict=False))


def _metadata(
    scraped_at: Any,
    event_url: Any,
    fight_url: Any,
    ingested_at: str,
) -> dict[str, Any]:
    return {
        "scraped_at": scraped_at,
        "ingested_at": ingested_at,
        "event_id": url_identifier(event_url, "/event-details/"),
        "fight_id": url_identifier(fight_url, "/fight-details/"),
    }


def _scraped_at(value: Any, source_file: Path) -> Any:
    """Use the extractor timestamp, or the legacy raw timestamp folder."""
    if isinstance(value, str) and value.strip():
        return value
    parent_timestamp = source_file.parent.name
    return parent_timestamp if parent_timestamp else None


def _data_with_metadata(row: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    data = {key: value for key, value in row.items() if key not in {"scraped_at", "ingested_at", "event_id", "fight_id"}}
    data.update(metadata)
    return data


def _write(rows: list[dict[str, Any]], category: str, filename: str, staged_at: datetime) -> Path:
    output = build_staging_output_path(category, filename, now=staged_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    _string_frame(rows).write_parquet(output)
    return output


def _stage_fighters(files: list[Path], category: str, staged_at: datetime, ingested_at: str) -> dict[str, Path]:
    rows: list[dict[str, Any]] = []
    for path in files:
        report = validate_fighters_file(path)
        if not report.valid:
            raise ValueError(f"Invalid fighters file {path}: " + "; ".join(x.message for x in report.errors))
        for row in _json(path):
            metadata = _metadata(_scraped_at(row.get("scraped_at"), path), None, None, ingested_at)
            metadata.pop("event_id")
            metadata.pop("fight_id")
            rows.append(_data_with_metadata(row, metadata))
    return {"fighters": _write(rows, category, "fighters.parquet", staged_at)}


def _stage_events(files: list[Path], category: str, staged_at: datetime, ingested_at: str) -> dict[str, Path]:
    events: list[dict[str, Any]] = []
    for path in files:
        report = validate_events_file(path)
        if not report.valid:
            raise ValueError(f"Invalid events file {path}: " + "; ".join(x.message for x in report.errors))
        payload = _json(path)
        metadata = _metadata(_scraped_at(payload.get("scraped_at"), path), payload["event"].get("event_link"), None, ingested_at)
        metadata.pop("fight_id")
        events.append(_data_with_metadata(payload["event"], metadata))
    return {"events": _write(events, category, "events.parquet", staged_at)}


def _stage_summaries(files: list[Path], category: str, staged_at: datetime, ingested_at: str) -> dict[str, Path]:
    rows: list[dict[str, Any]] = []
    for path in files:
        report = validate_fight_summary_file(path)
        if not report.valid:
            raise ValueError(f"Invalid fight-summary file {path}: " + "; ".join(x.message for x in report.errors))
        payload = _json(path)
        rows.append(_data_with_metadata(payload, _metadata(_scraped_at(payload.get("scraped_at"), path), payload.get("event_link"), payload.get("fight_link"), ingested_at)))
    return {"fight_summary": _write(rows, category, "fight_summary.parquet", staged_at)}


def _stage_details(files: list[Path], category: str, staged_at: datetime, ingested_at: str) -> dict[str, Path]:
    totals: list[dict[str, Any]] = []
    significant_strikes: list[dict[str, Any]] = []
    event_by_fight: dict[str, str] = {}
    for summary_path in sorted((RAW_ROOT / "fight_summary").rglob("*.json")):
        summary = _json(summary_path)
        fight_url = summary.get("fight_link")
        event_url = summary.get("event_link")
        if isinstance(fight_url, str) and isinstance(event_url, str) and fight_url and event_url:
            event_by_fight[fight_url] = event_url
    for path in files:
        report = validate_fight_details_file(path)
        if not report.valid:
            raise ValueError(f"Invalid fight-details file {path}: " + "; ".join(x.message for x in report.errors))
        payload = _json(path)
        event_url = payload.get("event_url") or event_by_fight.get(payload.get("fight_url"))
        if not event_url:
            raise ValueError(f"Could not resolve parent event for fight {payload.get('fight_url')} from fight summaries")
        metadata = _metadata(_scraped_at(payload.get("scraped_at"), path), event_url, payload.get("fight_url"), ingested_at)
        totals.extend(_data_with_metadata(row, metadata) for row in payload["totals"])
        significant_strikes.extend(_data_with_metadata(row, metadata) for row in payload["significant_strikes"])
    return {
        "totals": _write(totals, category, "totals.parquet", staged_at),
        "significant_strikes": _write(significant_strikes, category, "significant_strikes.parquet", staged_at),
    }


def stage_dataset(
    dataset: str,
    raw_root: str | Path = RAW_ROOT,
    now: datetime | None = None,
) -> dict[str, Path]:
    """Validate raw JSON and write a timestamped, string-only Parquet staging run."""
    root = Path(raw_root)
    aliases = {"fight_summary": "fight_summary", "fight_details": "fight_details", "fighters": "fighters", "events": "events"}
    if dataset not in aliases:
        raise ValueError(f"Unsupported dataset {dataset!r}; choose one of: {', '.join(sorted(aliases))}")
    category = aliases[dataset]
    files = sorted((root / category).rglob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found under {root / category}")
    staged_at = now or datetime.now()
    ingested_at = scraped_timestamp()
    if dataset == "fighters":
        return _stage_fighters(files, category, staged_at, ingested_at)
    if dataset == "events":
        return _stage_events(files, category, staged_at, ingested_at)
    if dataset == "fight_summary":
        return _stage_summaries(files, category, staged_at, ingested_at)
    return _stage_details(files, category, staged_at, ingested_at)
