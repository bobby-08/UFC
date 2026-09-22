from __future__ import annotations

from pathlib import Path

import duckdb

from .connection import DEFAULT_DB_PATH, get_connection


# These tables mirror the files written by the transformation layer. They are
# rebuilt from data/processed on each load so the database is reproducible from
# the processed Parquet outputs and never depends on raw or staging files.
TRANSFORMED_EVENTS_TABLE_SQL = """
CREATE TABLE events (
    event_id VARCHAR PRIMARY KEY,
    event_name VARCHAR,
    event_date DATE,
    event_location VARCHAR,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    transformed_at TIMESTAMPTZ
);
"""

TRANSFORMED_FIGHTERS_TABLE_SQL = """
CREATE TABLE fighters (
    fighter_id VARCHAR PRIMARY KEY,
    fighter_name VARCHAR,
    nickname VARCHAR,
    height_inches DOUBLE,
    weight_lbs DOUBLE,
    reach_inches DOUBLE,
    stance VARCHAR,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    transformed_at TIMESTAMPTZ
);
"""

FIGHTER_STATS_TABLE_SQL = """
CREATE TABLE fighter_stats (
    fighter_id VARCHAR PRIMARY KEY,
    wins BIGINT,
    losses BIGINT,
    draws BIGINT,
    belt BOOLEAN,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    transformed_at TIMESTAMPTZ
);
"""

TRANSFORMED_FIGHT_SUMMARY_TABLE_SQL = """
CREATE TABLE fight_summary (
    fight_id VARCHAR,
    event_id VARCHAR,
    event_name VARCHAR,
    bout_type VARCHAR,
    method VARCHAR,
    round BIGINT,
    time VARCHAR,
    time_seconds BIGINT,
    time_format VARCHAR,
    referee VARCHAR,
    details VARCHAR,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    winner VARCHAR,
    loser VARCHAR,
    fighter VARCHAR,
    opponent VARCHAR,
    fighter_result VARCHAR,
    nickname VARCHAR,
    transformed_at TIMESTAMPTZ,
    PRIMARY KEY (fight_id, fighter)
);
"""

TRANSFORMED_TOTALS_TABLE_SQL = """
CREATE TABLE totals (
    fight_id VARCHAR,
    event_id VARCHAR,
    round BIGINT,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    fighter VARCHAR,
    opponent VARCHAR,
    sig_str_landed BIGINT,
    sig_str_attempted BIGINT,
    total_str_landed BIGINT,
    total_str_attempted BIGINT,
    td_landed BIGINT,
    td_attempted BIGINT,
    sig_str_pct DOUBLE,
    td_pct DOUBLE,
    total_str_pct DOUBLE,
    kd BIGINT,
    sub_att BIGINT,
    rev BIGINT,
    ctrl_seconds BIGINT,
    transformed_at TIMESTAMPTZ,
    PRIMARY KEY (fight_id, round, fighter)
);
"""

TRANSFORMED_SIGNIFICANT_STRIKES_TABLE_SQL = """
CREATE TABLE significant_strikes (
    fight_id VARCHAR,
    event_id VARCHAR,
    round BIGINT,
    scraped_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    fighter VARCHAR,
    opponent VARCHAR,
    sig_str_landed BIGINT,
    sig_str_attempted BIGINT,
    sig_str_pct DOUBLE,
    head_landed BIGINT,
    head_attempted BIGINT,
    head_pct DOUBLE,
    body_landed BIGINT,
    body_attempted BIGINT,
    body_pct DOUBLE,
    leg_landed BIGINT,
    leg_attempted BIGINT,
    leg_pct DOUBLE,
    distance_landed BIGINT,
    distance_attempted BIGINT,
    distance_pct DOUBLE,
    clinch_landed BIGINT,
    clinch_attempted BIGINT,
    clinch_pct DOUBLE,
    ground_landed BIGINT,
    ground_attempted BIGINT,
    ground_pct DOUBLE,
    transformed_at TIMESTAMPTZ,
    PRIMARY KEY (fight_id, round, fighter)
);
"""


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


PIPELINE_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR PRIMARY KEY,
    dataset_name VARCHAR NOT NULL,
    source_url VARCHAR,
    status VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    output_path VARCHAR,
    record_count INTEGER,
    error_type VARCHAR,
    error_message VARCHAR,
    traceback VARCHAR
);
"""


PIPELINE_FILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_files (
    file_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    file_checksum VARCHAR,
    created_at TIMESTAMP NOT NULL
);
"""


DOWNLOADED_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS downloaded_events (
    event_id VARCHAR PRIMARY KEY,
    event_link VARCHAR NOT NULL UNIQUE,
    event_name VARCHAR NOT NULL,
    event_date DATE NOT NULL,
    file_path VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    file_checksum VARCHAR,
    downloaded_at TIMESTAMP NOT NULL
);
"""


DOWNLOADED_RESOURCES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS downloaded_resources (
    dataset_name VARCHAR NOT NULL,
    resource_id VARCHAR NOT NULL,
    event_id VARCHAR,
    file_path VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    file_checksum VARCHAR,
    downloaded_at TIMESTAMP NOT NULL,
    PRIMARY KEY (dataset_name, resource_id)
);
"""


EVENT_DATASET_STATUS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS event_dataset_status (
    event_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    completed_at TIMESTAMP,
    PRIMARY KEY (event_id, dataset_name)
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


def create_pipeline_runs_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the pipeline runs audit table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(PIPELINE_RUNS_TABLE_SQL)
        return

    connection.execute(PIPELINE_RUNS_TABLE_SQL)


def create_pipeline_files_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the pipeline files audit table in DuckDB if it does not already exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(PIPELINE_FILES_TABLE_SQL)
        return

    connection.execute(PIPELINE_FILES_TABLE_SQL)


def create_downloaded_events_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the event download checkpoint table if it does not exist."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(DOWNLOADED_EVENTS_TABLE_SQL)
        return

    connection.execute(DOWNLOADED_EVENTS_TABLE_SQL)


def create_downloaded_resources_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the fight/file download checkpoint table if needed."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(DOWNLOADED_RESOURCES_TABLE_SQL)
        return

    connection.execute(DOWNLOADED_RESOURCES_TABLE_SQL)


def create_event_dataset_status_table(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Create the per-event dataset completion table if needed."""
    if connection is None:
        with get_connection(db_path) as managed_connection:
            managed_connection.execute(EVENT_DATASET_STATUS_TABLE_SQL)
        return

    connection.execute(EVENT_DATASET_STATUS_TABLE_SQL)


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
    """Create the processed-data and pipeline-audit DuckDB schema."""
    create_transformed_schema(connection=connection, db_path=db_path)
    create_pipeline_runs_table(connection=connection, db_path=db_path)
    create_pipeline_files_table(connection=connection, db_path=db_path)
    create_downloaded_events_table(connection=connection, db_path=db_path)
    create_downloaded_resources_table(connection=connection, db_path=db_path)
    create_event_dataset_status_table(connection=connection, db_path=db_path)


def create_transformed_schema(
    connection: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Recreate tables to match the current processed Parquet schemas."""
    statements = {
        "events": TRANSFORMED_EVENTS_TABLE_SQL,
        "fighters": TRANSFORMED_FIGHTERS_TABLE_SQL,
        "fighter_stats": FIGHTER_STATS_TABLE_SQL,
        "fight_summary": TRANSFORMED_FIGHT_SUMMARY_TABLE_SQL,
        "totals": TRANSFORMED_TOTALS_TABLE_SQL,
        "significant_strikes": TRANSFORMED_SIGNIFICANT_STRIKES_TABLE_SQL,
    }

    def create(target: duckdb.DuckDBPyConnection) -> None:
        for table, statement in statements.items():
            target.execute(f'DROP TABLE IF EXISTS "{table}"')
            target.execute(statement)

    if connection is None:
        with get_connection(db_path) as managed_connection:
            create(managed_connection)
    else:
        create(connection)
