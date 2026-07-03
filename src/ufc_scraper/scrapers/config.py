from __future__ import annotations

BASE_URL = "http://www.ufcstats.com"

EVENTS_PATH = "statistics/events/completed?page=all"
FIGHTERS_PATH = "statistics/fighters?page=all"
EVENT_DETAILS_PATH = "event-details"
FIGHT_DETAILS_PATH = "fight-details"

EVENTS_URL = f"{BASE_URL}/{EVENTS_PATH}"
FIGHTERS_URL = f"{BASE_URL}/{FIGHTERS_PATH}"
EVENT_DETAILS_URL = f"{BASE_URL}/{EVENT_DETAILS_PATH}"
FIGHT_DETAILS_URL = f"{BASE_URL}/{FIGHT_DETAILS_PATH}"

# Backward-compatible aliases used by older modules and scripts.
COMPLETED_EVENTS_PATH = EVENTS_PATH
ALL_FIGHTERS_PATH = FIGHTERS_PATH
COMPLETED_EVENTS_URL = EVENTS_URL
ALL_FIGHTERS_URL = FIGHTERS_URL


def build_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
