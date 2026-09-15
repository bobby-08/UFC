from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from ..storage import build_staging_output_path
from ..validation import validate_fight_details_payload

ROOT = Path(__file__).resolve().parents[3]
RAW_FIGHT_DETAILS_ROOT = ROOT / "data" / "raw" / "fight_details"
TOTALS_FIELDS = ["kd", "sig_str", "sig_str_pct", "total_str", "td", "td_pct", "sub_att", "rev", "ctrl"]
SIG_FIELDS = ["sig_str", "sig_str_pct", "head", "body", "leg", "distance", "clinch", "ground"]


def _load_payload(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return validate_fight_details_payload(json.load(handle))


def _explode_rows(payload: dict[str, Any], section: str, fields: list[str], source_file: Path, staged_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair in payload[section]:
        for suffix in ("1", "2"):
            rows.append({
                "fight_link": payload["fight_url"],
                "round_label": pair["round_label"],
                "fighter": pair[f"fighter{suffix}"],
                **{field: pair[f"{field}_fighter{suffix}"] for field in fields},
                "source_file": str(source_file),
                "staged_at": staged_at,
            })
    return rows


def stage_fight_details(
    raw_root: Path = RAW_FIGHT_DETAILS_ROOT,
    staging_category: str = "fight_details",
    now: datetime | None = None,
) -> dict[str, Path]:
    """Validate raw fight-details JSON and write normalized Parquet staging files."""
    raw_files = sorted(raw_root.rglob("*.json"))
    if not raw_files:
        raise FileNotFoundError(f"No raw fight-details JSON files found under {raw_root}")
    staged_at_dt = now or datetime.now()
    staged_at = staged_at_dt.isoformat(timespec="seconds")
    totals: list[dict[str, Any]] = []
    sigs: list[dict[str, Any]] = []
    for raw_file in raw_files:
        payload = _load_payload(raw_file)
        totals.extend(_explode_rows(payload, "totals", TOTALS_FIELDS, raw_file, staged_at))
        sigs.extend(_explode_rows(payload, "significant_strikes", SIG_FIELDS, raw_file, staged_at))

    totals_output = build_staging_output_path(staging_category, "totals.parquet", now=staged_at_dt)
    sig_output = build_staging_output_path(staging_category, "significant_strikes.parquet", now=staged_at_dt)
    totals_output.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(totals).write_parquet(totals_output)
    pl.DataFrame(sigs).write_parquet(sig_output)
    return {"totals": totals_output, "significant_strikes": sig_output}
