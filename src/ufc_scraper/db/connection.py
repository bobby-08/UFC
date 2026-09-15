from __future__ import annotations

from pathlib import Path

import duckdb

from ..logging import get_logger


LOGGER = get_logger(__name__, stage="database")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "db" / "ufc.duckdb"


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection for the UFC project database."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Opening DuckDB connection path=%s", db_file)
    return duckdb.connect(str(db_file))
