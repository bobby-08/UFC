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
    height VARCHAR,
    weight VARCHAR,
    reach VARCHAR,
    stance VARCHAR,
    wins VARCHAR,
    losses VARCHAR,
    draws VARCHAR,
    belt VARCHAR
);
"""


EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_link VARCHAR PRIMARY KEY,
    event_name VARCHAR NOT NULL,
    event_date VARCHAR,
    event_location VARCHAR
);
"""


EVENT_FIGHTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS event_fights (
    fight_link VARCHAR PRIMARY KEY,
    fighter_1 VARCHAR,
    fighter_2 VARCHAR,
    result_fighter_1 VARCHAR,
    result_fighter_2 VARCHAR,
    weight_class VARCHAR,
    method VARCHAR,
    round VARCHAR,
    time VARCHAR
);
"""


FIGHTS_SUMMARY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fights_summary (
    fight_link VARCHAR PRIMARY KEY,
    event_link VARCHAR NOT NULL,
    event_name VARCHAR,
    fighter_1_name VARCHAR NOT NULL,
    fighter_1_result VARCHAR,
    fighter_1_nickname VARCHAR,
    fighter_2_name VARCHAR NOT NULL,
    fighter_2_result VARCHAR,
    fighter_2_nickname VARCHAR,
    result VARCHAR,
    winner VARCHAR,
    loser VARCHAR,
    bout_type VARCHAR,
    weight_class VARCHAR,
    method VARCHAR,
    round VARCHAR,
    time VARCHAR,
    time_format VARCHAR,
    referee VARCHAR,
    details VARCHAR
);
"""


FIGHT_TOTALS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fight_totals (
    fight_link VARCHAR,
    round_label VARCHAR,
    fighter VARCHAR,
    kd VARCHAR,
    sig_str VARCHAR,
    sig_str_pct VARCHAR,
    total_str VARCHAR,
    td VARCHAR,
    td_pct VARCHAR,
    sub_att VARCHAR,
    rev VARCHAR,
    ctrl VARCHAR,
    PRIMARY KEY (fight_link, round_label, fighter)
);
"""


FIGHT_SIGNIFICANT_STRIKES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fight_significant_strikes (
    fight_link VARCHAR,
    round_label VARCHAR,
    fighter VARCHAR,
    sig_str VARCHAR,
    sig_str_pct VARCHAR,
    head VARCHAR,
    body VARCHAR,
    leg VARCHAR,
    distance VARCHAR,
    clinch VARCHAR,
    ground VARCHAR,
    PRIMARY KEY (fight_link, round_label, fighter)
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


def create_event_fights_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the event fights table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(EVENT_FIGHTS_TABLE_SQL)
        return

    connection.execute(EVENT_FIGHTS_TABLE_SQL)


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


def create_fight_totals_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the fight totals table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(FIGHT_TOTALS_TABLE_SQL)
        return

    connection.execute(FIGHT_TOTALS_TABLE_SQL)


def create_fight_significant_strikes_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the fight significant strikes table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(FIGHT_SIGNIFICANT_STRIKES_TABLE_SQL)
        return

    connection.execute(FIGHT_SIGNIFICANT_STRIKES_TABLE_SQL)


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
    create_event_fights_table(connection=connection, db_path=db_path)
    create_fights_summary_table(connection=connection, db_path=db_path)
    create_fight_totals_table(connection=connection, db_path=db_path)
    create_fight_significant_strikes_table(connection=connection, db_path=db_path)
