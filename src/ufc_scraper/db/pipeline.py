from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from traceback import format_exc
from uuid import uuid4

import duckdb

from .schema import (
    create_downloaded_events_table,
    create_downloaded_resources_table,
    create_event_dataset_status_table,
    create_pipeline_files_table,
    create_pipeline_runs_table,
)
from ..logging import get_logger


LOGGER = get_logger(__name__, stage="database")


@dataclass(slots=True)
class PipelineRun:
    run_id: str
    dataset_name: str
    source_url: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    output_path: str | None = None
    record_count: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def checksum_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_pipeline_audit_tables(connection: duckdb.DuckDBPyConnection) -> None:
    create_pipeline_runs_table(connection=connection)
    create_pipeline_files_table(connection=connection)
    create_downloaded_events_table(connection=connection)
    create_downloaded_resources_table(connection=connection)
    create_event_dataset_status_table(connection=connection)


def parse_event_date(value: str) -> date:
    """Parse the date formats emitted by UFCStats into a comparable date."""

    for pattern in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported UFC event date: {value!r}")


def latest_downloaded_event_date(connection: duckdb.DuckDBPyConnection) -> date | None:
    """Return the newest successfully registered event date."""

    ensure_pipeline_audit_tables(connection)
    rows = connection.execute(
        "SELECT event_date, file_path FROM downloaded_events"
    ).fetchall()
    valid_dates = [event_date for event_date, file_path in rows if Path(file_path).is_file()]
    return max(valid_dates) if valid_dates else None


def event_is_already_downloaded(
    connection: duckdb.DuckDBPyConnection,
    event_id: str,
    event_date: date,
    *,
    use_date_cutoff: bool = True,
) -> bool:
    """Return whether an event is already covered by the download checkpoint.

    The date comparison is inclusive so the same event date cannot be downloaded
    twice during incremental runs. Historical backfills can disable that
    comparison and rely on the event ID/file checkpoint instead.
    """

    ensure_pipeline_audit_tables(connection)
    found = connection.execute(
        "SELECT file_path FROM downloaded_events WHERE event_id = ? LIMIT 1",
        [event_id],
    ).fetchone()
    if found is not None and Path(found[0]).is_file():
        return True

    if found is not None:
        LOGGER.warning(
            "Event checkpoint exists but its file is missing; reprocessing event_id=%s path=%s",
            event_id,
            found[0],
        )
        return False

    if not use_date_cutoff:
        return False

    checkpoint = latest_downloaded_event_date(connection)
    return checkpoint is not None and event_date <= checkpoint


def register_downloaded_event(
    connection: duckdb.DuckDBPyConnection,
    event_id: str,
    event_link: str,
    event_name: str,
    event_date: date,
    file_path: str | Path,
) -> None:
    """Register a successfully written event file and its checksum."""

    ensure_pipeline_audit_tables(connection)
    path = Path(file_path)
    connection.execute(
        """
        INSERT INTO downloaded_events (
            event_id, event_link, event_name, event_date, file_path,
            file_name, file_checksum, downloaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO UPDATE SET
                event_link = excluded.event_link,
                event_name = excluded.event_name,
                event_date = excluded.event_date,
                file_path = excluded.file_path,
                file_name = excluded.file_name,
                file_checksum = excluded.file_checksum,
                downloaded_at = excluded.downloaded_at
        """,
        [
            event_id,
            event_link,
            event_name,
            event_date,
            str(path),
            path.name,
            checksum_file(path) if path.exists() else None,
            utcnow(),
        ],
    )
    LOGGER.info("Registered downloaded event_id=%s event_date=%s path=%s", event_id, event_date, path)


def resource_is_downloaded(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
    resource_id: str,
) -> bool:
    """Return whether a dataset resource has already been downloaded."""

    ensure_pipeline_audit_tables(connection)
    row = connection.execute(
        """
        SELECT file_path
        FROM downloaded_resources
        WHERE dataset_name = ? AND resource_id = ?
        LIMIT 1
        """,
        [dataset_name, resource_id],
    ).fetchone()
    if row is None:
        return False
    if Path(row[0]).is_file():
        return True
    LOGGER.warning(
        "Resource checkpoint exists but its file is missing; reprocessing dataset=%s resource_id=%s path=%s",
        dataset_name,
        resource_id,
        row[0],
    )
    return False


def register_downloaded_resource(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
    resource_id: str,
    file_path: str | Path,
    event_id: str | None = None,
) -> None:
    """Register one downloaded fight-level resource and its checksum."""

    ensure_pipeline_audit_tables(connection)
    path = Path(file_path)
    connection.execute(
        """
        INSERT INTO downloaded_resources (
            dataset_name, resource_id, event_id, file_path, file_name,
            file_checksum, downloaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (dataset_name, resource_id) DO UPDATE SET
                event_id = excluded.event_id,
                file_path = excluded.file_path,
                file_name = excluded.file_name,
                file_checksum = excluded.file_checksum,
                downloaded_at = excluded.downloaded_at
        """,
        [
            dataset_name,
            resource_id,
            event_id,
            str(path),
            path.name,
            checksum_file(path) if path.exists() else None,
            utcnow(),
        ],
    )


def event_dataset_is_complete(
    connection: duckdb.DuckDBPyConnection,
    event_id: str,
    dataset_name: str,
) -> bool:
    """Return whether an event dataset finished successfully."""

    ensure_pipeline_audit_tables(connection)
    row = connection.execute(
        """
        SELECT 1
        FROM event_dataset_status
        WHERE event_id = ? AND dataset_name = ? AND status = 'success'
        LIMIT 1
        """,
        [event_id, dataset_name],
    ).fetchone()
    if row is None:
        return False

    resource_paths = connection.execute(
        """
        SELECT file_path
        FROM downloaded_resources
        WHERE event_id = ? AND dataset_name = ?
          AND file_path IS NOT NULL
        """,
        [event_id, dataset_name],
    ).fetchall()
    missing_file = next(
        (row[0] for row in resource_paths if not Path(row[0]).is_file()),
        None,
    )
    if missing_file is not None:
        LOGGER.warning(
            "Event dataset checkpoint exists but a file is missing; reprocessing event_id=%s dataset=%s path=%s",
            event_id,
            dataset_name,
            missing_file,
        )
        return False
    return True


def mark_event_dataset_complete(
    connection: duckdb.DuckDBPyConnection,
    event_id: str,
    dataset_name: str,
    record_count: int,
) -> None:
    """Mark all resources for one event/dataset as successfully processed."""

    ensure_pipeline_audit_tables(connection)
    connection.execute(
        """
        INSERT INTO event_dataset_status (
            event_id, dataset_name, status, record_count, completed_at
        )
        VALUES (?, ?, 'success', ?, ?)
        ON CONFLICT (event_id, dataset_name) DO UPDATE SET
            status = excluded.status,
            record_count = excluded.record_count,
            completed_at = excluded.completed_at
        """,
        [event_id, dataset_name, record_count, utcnow()],
    )


def start_pipeline_run(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
    source_url: str | None = None,
) -> PipelineRun:
    ensure_pipeline_audit_tables(connection)
    run = PipelineRun(
        run_id=str(uuid4()),
        dataset_name=dataset_name,
        source_url=source_url,
        status="running",
        started_at=utcnow(),
    )
    connection.execute(
        """
        INSERT INTO pipeline_runs (
            run_id, dataset_name, source_url, status, started_at, finished_at,
            output_path, record_count, error_type, error_message, traceback
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run.run_id,
            run.dataset_name,
            run.source_url,
            run.status,
            run.started_at,
            run.finished_at,
            run.output_path,
            run.record_count,
            run.error_type,
            run.error_message,
            run.traceback,
        ],
    )
    LOGGER.info("Started pipeline run_id=%s dataset=%s", run.run_id, dataset_name)
    return run


def register_pipeline_file(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    dataset_name: str,
    file_path: str | Path,
) -> str:
    ensure_pipeline_audit_tables(connection)
    path = Path(file_path)
    file_id = str(uuid4())
    checksum = checksum_file(path) if path.exists() else None
    file_size_bytes = path.stat().st_size if path.exists() else None
    connection.execute(
        """
        INSERT INTO pipeline_files (
            file_id, run_id, dataset_name, file_path, file_name,
            file_size_bytes, file_checksum, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            file_id,
            run_id,
            dataset_name,
            str(path),
            path.name,
            file_size_bytes,
            checksum,
            utcnow(),
        ],
    )
    LOGGER.debug("Registered pipeline file run_id=%s path=%s", run_id, path)
    return file_id


def finish_pipeline_run_success(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    output_path: str | Path | None = None,
    record_count: int | None = None,
) -> None:
    connection.execute(
        """
        UPDATE pipeline_runs
        SET status = ?, finished_at = ?, output_path = ?, record_count = ?,
            error_type = NULL, error_message = NULL, traceback = NULL
        WHERE run_id = ?
        """,
        ["success", utcnow(), str(output_path) if output_path is not None else None, record_count, run_id],
    )
    LOGGER.info("Finished pipeline run_id=%s status=success records=%s", run_id, record_count)


def finish_pipeline_run_failure(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    error: BaseException,
    output_path: str | Path | None = None,
    record_count: int | None = None,
) -> None:
    connection.execute(
        """
        UPDATE pipeline_runs
        SET status = ?, finished_at = ?, output_path = ?, record_count = ?,
            error_type = ?, error_message = ?, traceback = ?
        WHERE run_id = ?
        """,
        [
            "failed",
            utcnow(),
            str(output_path) if output_path is not None else None,
            record_count,
            type(error).__name__,
            str(error),
            format_exc(),
            run_id,
        ],
    )
    LOGGER.error("Finished pipeline run_id=%s status=failed error_type=%s error=%s", run_id, type(error).__name__, error)
