"""Move successfully transformed raw JSON into the configured raw archive."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ufc_scraper.config import project_path
from ufc_scraper.db import ensure_pipeline_audit_tables, get_connection
from ufc_scraper.logging import get_logger


LOGGER = get_logger(__name__, stage="pipeline")


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _move_raw_files(raw_root: Path, archive_root: Path) -> int:
    if not raw_root.exists():
        LOGGER.info("Raw directory does not exist; nothing to archive path=%s", raw_root)
        return 0

    raw_root.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)
    raw_root_resolved = raw_root.resolve()
    archive_root_resolved = archive_root.resolve()

    moved = 0
    for source in sorted(raw_root_resolved.rglob("*.json")):
        if not source.is_file():
            continue
        if raw_root_resolved not in source.parents:
            raise RuntimeError(f"Refusing to archive a file outside raw root: {source}")

        destination = archive_root_resolved / source.relative_to(raw_root_resolved)
        if archive_root_resolved not in destination.resolve().parents:
            raise RuntimeError(f"Refusing to write outside archive root: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            if _checksum(source) != _checksum(destination):
                raise FileExistsError(
                    f"Archive destination already exists with different content: {destination}"
                )
            source.unlink()
            LOGGER.info("Removed duplicate raw file already archived path=%s", source)
        else:
            shutil.move(str(source), str(destination))
            LOGGER.info("Archived raw file source=%s destination=%s", source, destination)
        moved += 1

    for directory in sorted(
        (path for path in raw_root_resolved.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if directory != raw_root_resolved and not any(directory.iterdir()):
            directory.rmdir()

    return moved


def _update_audit_paths(raw_root: Path, archive_root: Path) -> None:
    """Keep download checkpoints valid after their files move to the archive."""

    archive_root_resolved = archive_root.resolve()
    archived_files = sorted(archive_root_resolved.rglob("*.json"))
    if not archived_files:
        return

    with get_connection() as connection:
        ensure_pipeline_audit_tables(connection)
        connection.execute("BEGIN TRANSACTION")
        try:
            for archived_path in archived_files:
                source_path = raw_root / archived_path.relative_to(archive_root_resolved)
                old_path = str(source_path)
                new_path = str(archived_path)
                connection.execute(
                    "UPDATE downloaded_events SET file_path = ? WHERE file_path = ?",
                    [new_path, old_path],
                )
                connection.execute(
                    "UPDATE downloaded_resources SET file_path = ? WHERE file_path = ?",
                    [new_path, old_path],
                )
                connection.execute(
                    "UPDATE pipeline_files SET file_path = ? WHERE file_path = ?",
                    [new_path, old_path],
                )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    LOGGER.info("Updated DuckDB audit paths for archived raw files=%d", len(archived_files))


def main() -> int:
    raw_root = project_path("raw", "root").resolve()
    archive_root = project_path("archive", "raw").resolve()
    if raw_root == archive_root or raw_root in archive_root.parents or archive_root in raw_root.parents:
        raise RuntimeError(
            f"Raw and archive roots must be separate directories: raw={raw_root} archive={archive_root}"
        )

    count = _move_raw_files(raw_root, archive_root)
    _update_audit_paths(raw_root, archive_root)
    LOGGER.info(
        "Raw archival completed files_archived=%d source=%s archive=%s",
        count,
        raw_root,
        archive_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
