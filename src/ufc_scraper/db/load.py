from __future__ import annotations

from pathlib import Path

import duckdb

from .schema import create_fight_significant_strikes_table, create_fight_totals_table


def load_fight_details_staging(
    connection: duckdb.DuckDBPyConnection,
    totals_path: str | Path,
    significant_strikes_path: str | Path,
) -> dict[str, int]:
    """Idempotently load normalized fight-details Parquet files into DuckDB."""
    create_fight_totals_table(connection=connection)
    create_fight_significant_strikes_table(connection=connection)
    totals_columns = ["fight_link", "round_label", "fighter", "kd", "sig_str", "sig_str_pct", "total_str", "td", "td_pct", "sub_att", "rev", "ctrl"]
    sig_columns = ["fight_link", "round_label", "fighter", "sig_str", "sig_str_pct", "head", "body", "leg", "distance", "clinch", "ground"]
    connection.execute("BEGIN")
    try:
        connection.execute("INSERT OR REPLACE INTO fight_totals SELECT " + ", ".join(totals_columns) + " FROM read_parquet(?)", [str(Path(totals_path))])
        connection.execute("INSERT OR REPLACE INTO fight_significant_strikes SELECT " + ", ".join(sig_columns) + " FROM read_parquet(?)", [str(Path(significant_strikes_path))])
        totals_count = connection.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(Path(totals_path))]).fetchone()[0]
        sig_count = connection.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(Path(significant_strikes_path))]).fetchone()[0]
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return {"totals": totals_count, "significant_strikes": sig_count}
