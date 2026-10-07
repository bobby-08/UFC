"""Restore and publish project data to Azure Blob Storage.

Blob Storage is the durable copy. Local files are used as working files while
the DAG runs and are removed only after every upload completes successfully.
The DuckDB file is synced as a closed file at DAG boundaries; it is never
opened directly from Blob Storage.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import shutil
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA_ROOT = ROOT / "data"
MANAGED_PATHS = ("raw", "archive/raw", "processed", "db")
TRANSIENT_PATHS = ("staging",)
ARCHIVE_PREFIX = "archive/raw/"

LOGGER = logging.getLogger("ufc.blob_data_sync")


def _configured_container():
    """Create a Blob container client using the VM's managed identity."""

    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "").strip()
    if not account_name or not container_name:
        raise RuntimeError(
            "Set AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_CONTAINER when "
            "UFC_DATA_BACKEND=azure_blob."
        )

    from azure.identity import ManagedIdentityCredential
    from azure.storage.blob import BlobServiceClient

    credential = ManagedIdentityCredential()
    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential,
    )
    container = service.get_container_client(container_name)
    container.get_container_properties()
    return credential, service, container


def _managed_prefixes() -> tuple[str, ...]:
    return tuple(f"{path.rstrip('/')}/" for path in MANAGED_PATHS)


def _local_path_for_blob(blob_name: str) -> Path:
    """Resolve a managed blob name beneath data/, rejecting path traversal."""

    target = (DATA_ROOT / Path(*PurePosixPath(blob_name).parts)).resolve()
    try:
        target.relative_to(DATA_ROOT.resolve())
    except ValueError as error:
        raise RuntimeError(f"Blob name resolves outside the data directory: {blob_name}") from error
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_from_blob(container) -> int:
    """Download managed data that is not already present in the work area."""

    downloaded = 0
    for prefix in _managed_prefixes():
        for blob in container.list_blobs(name_starts_with=prefix):
            if blob.name.endswith("/"):
                continue
            target = _local_path_for_blob(blob.name)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            blob_client = container.get_blob_client(blob.name)
            with target.open("wb") as stream:
                blob_client.download_blob().readinto(stream)
            downloaded += 1
            LOGGER.info("Restored blob=%s", blob.name)

    LOGGER.info("Blob restore completed files_downloaded=%d", downloaded)
    return downloaded


def _local_managed_files() -> list[Path]:
    files: list[Path] = []
    for relative_root in MANAGED_PATHS:
        root = DATA_ROOT / relative_root
        if not root.exists():
            continue
        if root.is_symlink():
            raise RuntimeError(f"Refusing to sync a symlinked data path: {root}")
        files.extend(
            path for path in root.rglob("*")
            if path.is_file() and not path.is_symlink() and path.name != ".gitkeep"
        )
    return sorted(files)


def _upload_file(container, path: Path) -> bool:
    """Upload one file, preserving unchanged immutable archive blobs."""

    from azure.core.exceptions import ResourceNotFoundError
    from azure.storage.blob import StandardBlobTier

    blob_name = path.relative_to(DATA_ROOT).as_posix()
    blob_client = container.get_blob_client(blob_name)
    digest = _sha256(path)

    try:
        properties = blob_client.get_blob_properties()
    except ResourceNotFoundError:
        properties = None

    if properties is not None:
        remote_digest = (properties.metadata or {}).get("sha256")
        is_archive = blob_name.startswith(ARCHIVE_PREFIX)
        if is_archive:
            remote_tier = getattr(properties, "blob_tier", None)
            if hasattr(remote_tier, "value"):
                remote_tier = remote_tier.value
            if str(remote_tier).lower() != "cool":
                blob_client.set_standard_blob_tier(StandardBlobTier.COOL)
        if remote_digest == digest:
            LOGGER.debug("Blob is unchanged; skipped blob=%s", blob_name)
            return False
        # Existing archive paths are immutable timestamped outputs. Avoid
        # rewriting legacy archive objects that predate checksum metadata.
        if is_archive:
            if not remote_digest and properties.size == path.stat().st_size:
                LOGGER.info("Existing archive blob retained blob=%s", blob_name)
                return False
            raise RuntimeError(
                f"Refusing to overwrite immutable Cool-tier archive blob with different content: {blob_name}"
            )

    options = {
        "overwrite": True,
        "metadata": {"sha256": digest},
    }
    if blob_name.startswith(ARCHIVE_PREFIX):
        options["standard_blob_tier"] = StandardBlobTier.COOL

    with path.open("rb") as stream:
        blob_client.upload_blob(stream, **options)
    LOGGER.info(
        "Published blob=%s tier=%s",
        blob_name,
        "cool" if blob_name.startswith(ARCHIVE_PREFIX) else "default",
    )
    return True


def _clear_local_managed_data() -> int:
    removed = 0
    for relative_root in (*MANAGED_PATHS, *TRANSIENT_PATHS):
        root = DATA_ROOT / relative_root
        if not root.exists():
            continue
        if root.is_symlink():
            raise RuntimeError(f"Refusing to clean a symlinked data path: {root}")
        for child in root.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
            removed += 1
    return removed


def publish_to_blob(container) -> tuple[int, int]:
    """Upload managed data, then remove local work files after success."""

    published = 0
    files = _local_managed_files()
    for path in files:
        published += int(_upload_file(container, path))

    removed = _clear_local_managed_data()
    LOGGER.info(
        "Blob publish completed files_considered=%d files_uploaded=%d local_entries_removed=%d",
        len(files),
        published,
        removed,
    )
    return published, removed


def main() -> int:
    logging.basicConfig(
        level=os.getenv("UFC_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("restore", "publish"))
    args = parser.parse_args()

    backend = os.getenv("UFC_DATA_BACKEND", "local").strip().lower()
    if backend in ("", "local"):
        LOGGER.info("UFC_DATA_BACKEND=local; Blob synchronization skipped")
        return 0
    if backend != "azure_blob":
        raise RuntimeError(f"Unsupported UFC_DATA_BACKEND: {backend}")

    credential, service, container = _configured_container()
    try:
        if args.action == "restore":
            restore_from_blob(container)
        else:
            publish_to_blob(container)
    finally:
        service.close()
        credential.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
