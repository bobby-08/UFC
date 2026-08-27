from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from traceback import format_exc
from uuid import uuid4

import duckdb

from .schema import create_pipeline_files_table, create_pipeline_runs_table


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
