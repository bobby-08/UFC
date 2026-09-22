"""Run relationship and integrity checks against the loaded DuckDB tables."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.db import get_connection
from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="database")


def _count(connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])


def _assert_no_rows(connection, name: str, query: str) -> None:
    count = _count(connection, query)
    if count:
        raise RuntimeError(f"Database quality check failed: {name} violations={count}")
    LOGGER.info("Database quality check passed name=%s", name)


def main() -> int:
    LOGGER.info("Starting DuckDB relationship and integrity checks")
    with get_connection() as connection:
        tables = {
            row[0]
            for row in connection.execute("SHOW TABLES").fetchall()
        }
        required = {
            "events",
            "fighters",
            "fighter_stats",
            "fight_summary",
            "totals",
            "significant_strikes",
        }
        missing_tables = sorted(required - tables)
        if missing_tables:
            raise RuntimeError(f"Database quality check failed: missing tables={missing_tables}")

        for table in sorted(required):
            rows = _count(connection, f'SELECT COUNT(*) FROM "{table}"')
            if rows == 0:
                raise RuntimeError(f"Database quality check failed: table={table} is empty")
            LOGGER.info("Database table check passed table=%s rows=%d", table, rows)

        _assert_no_rows(
            connection,
            "fighter_stats_without_fighters",
            """
            SELECT COUNT(*)
            FROM fighter_stats stats
            LEFT JOIN fighters f USING (fighter_id)
            WHERE f.fighter_id IS NULL
            """,
        )
        _assert_no_rows(
            connection,
            "fight_summary_without_events",
            """
            SELECT COUNT(*)
            FROM fight_summary fights
            LEFT JOIN events e USING (event_id)
            WHERE e.event_id IS NULL
            """,
        )
        _assert_no_rows(
            connection,
            "totals_without_summary",
            """
            SELECT COUNT(*)
            FROM totals stats
            LEFT JOIN fight_summary fights USING (fight_id)
            WHERE fights.fight_id IS NULL
            """,
        )
        _assert_no_rows(
            connection,
            "significant_strikes_without_summary",
            """
            SELECT COUNT(*)
            FROM significant_strikes stats
            LEFT JOIN fight_summary fights USING (fight_id)
            WHERE fights.fight_id IS NULL
            """,
        )
        _assert_no_rows(
            connection,
            "null_primary_keys",
            """
            SELECT COUNT(*) FROM (
                SELECT event_id FROM events WHERE event_id IS NULL
                UNION ALL
                SELECT fighter_id FROM fighters WHERE fighter_id IS NULL
                UNION ALL
                SELECT fighter_id FROM fighter_stats WHERE fighter_id IS NULL
                UNION ALL
                SELECT fight_id FROM fight_summary WHERE fight_id IS NULL
                UNION ALL
                SELECT fight_id FROM totals WHERE fight_id IS NULL
                UNION ALL
                SELECT fight_id FROM significant_strikes WHERE fight_id IS NULL
            )
            """,
        )

    LOGGER.info("DuckDB relationship and integrity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
