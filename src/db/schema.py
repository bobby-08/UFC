from __future__ import annotations

from pathlib import Path

import duckdb

from .connection import DEFAULT_DB_PATH, get_connection


FIGHTERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fighters (
    fighter_id VARCHAR PRIMARY KEY,
    fighter_link VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    nickname VARCHAR,
    height_in DOUBLE,
    weight_lbs DOUBLE,
    reach_in DOUBLE,
    stance VARCHAR,
    wins INTEGER,
    losses INTEGER,
    draws INTEGER,
    belt VARCHAR
);
"""


EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_link VARCHAR PRIMARY KEY,
    event_name VARCHAR NOT NULL,
    event_date DATE,
    event_location VARCHAR
);
"""


FIGHTS_SUMMARY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fights_summary (
    fight_link VARCHAR PRIMARY KEY,
    event_link VARCHAR NOT NULL,
    fighter_1_name VARCHAR NOT NULL,
    fighter_2_name VARCHAR NOT NULL,
    result VARCHAR,
    weight_class VARCHAR,
    method VARCHAR,
    round INTEGER,
    time VARCHAR
);
"""


def create_fighters_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the fighters table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(FIGHTERS_TABLE_SQL)
        return

    connection.execute(FIGHTERS_TABLE_SQL)


def create_events_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the events table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(EVENTS_TABLE_SQL)
        return

    connection.execute(EVENTS_TABLE_SQL)


def create_fights_summary_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the fights summary table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(FIGHTS_SUMMARY_TABLE_SQL)
        return

    connection.execute(FIGHTS_SUMMARY_TABLE_SQL)


def create_fights_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Backward-compatible alias for create_fights_summary_table()."""
    create_fights_summary_table(connection=connection, db_path=db_path)


def create_schema(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the current DuckDB schema for the UFC project."""
    create_fighters_table(connection=connection, db_path=db_path)
    create_events_table(connection=connection, db_path=db_path)
    create_fights_summary_table(connection=connection, db_path=db_path)