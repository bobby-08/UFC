from __future__ import annotations

BASE_URL = "http://www.ufcstats.com"

EVENTS_PATH = "statistics/events/completed?page=all"
FIGHTERS_PATH = "statistics/fighters?page=all"

EVENT_DETAILS_PATH = "event-details"
FIGHT_DETAILS_PATH = "fight-details"


def build_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"