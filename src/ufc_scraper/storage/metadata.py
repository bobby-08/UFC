from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def scraped_timestamp(now: datetime | None = None) -> str:
    """Return an unambiguous UTC extraction timestamp."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="seconds")


def url_identifier(value: Any, path_prefix: str) -> str | None:
    """Return the final UFCStats URL path component, when it matches a resource."""
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.path.startswith(path_prefix):
        identifier = parsed.path.rstrip("/").split("/")[-1]
        return identifier or None
    return None
