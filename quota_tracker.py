"""
Tracks daily Gemini API call counts in a local JSON file.
Used to enforce the free-tier quota and prioritise formats.
"""
import json
import os
from datetime import datetime, timezone
from config import GEMINI_QUOTA_LIMIT, GEMINI_QUOTA_FILE


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        with open(GEMINI_QUOTA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    os.makedirs(os.path.dirname(GEMINI_QUOTA_FILE), exist_ok=True)
    with open(GEMINI_QUOTA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def increment(calls: int = 1):
    """Record that `calls` Gemini API calls were made today."""
    data = _load()
    today = _today()
    data[today] = data.get(today, 0) + calls
    _save(data)


def get_used() -> int:
    """Return how many Gemini calls have been made today (UTC)."""
    return _load().get(_today(), 0)


def get_remaining() -> int:
    """Return how many Gemini calls remain before the daily limit."""
    return max(0, GEMINI_QUOTA_LIMIT - get_used())


def can_proceed(needed: int = 2) -> bool:
    """
    Check whether there are enough quota calls remaining.
    Prints a warning and returns False if not enough quota is available.
    """
    remaining = get_remaining()
    if remaining < needed:
        print(
            f"⚠️  Gemini quota: {get_used()}/{GEMINI_QUOTA_LIMIT} used today. "
            f"Need {needed} more but only {remaining} remain. Skipping."
        )
        return False
    return True


def status() -> str:
    used = get_used()
    remaining = get_remaining()
    return f"Gemini quota: {used}/{GEMINI_QUOTA_LIMIT} used today, {remaining} remaining"
