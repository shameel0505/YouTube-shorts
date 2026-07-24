import os
import json
from datetime import datetime, timezone

STATE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory", "pipeline_state.json"))
MAX_DAILY_RETRIES = 3  # Max fresh-run attempts per day before giving up


def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            # Check for day rollover — if it's a new UTC day, always reset
            if data.get("current_day") != _get_current_utc_day():
                return _default_state()
            return data
    except Exception:
        return _default_state()


def _save_state(data: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def _get_current_utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_current_utc_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict:
    return {
        "current_day": _get_current_utc_day(),
        "status": "pending",   # pending, running, posted, failed, skipped
        "posted_formats": [],  # Track formats successfully posted today (e.g. ["1", "2"])
        "mode": None,          # fresh, resume
        "started_at": None,
        "posted_at": None,
        "last_updated": _get_current_utc_time(),
        "active_render": False,
        "last_error": None,
        "retry_count": 0,      # How many fresh runs attempted today
    }


def get_state() -> dict:
    return _load_state()


def can_retry_today() -> bool:
    """Returns True if we haven't exceeded today's max retry attempts."""
    state = _load_state()
    return state.get("retry_count", 0) < MAX_DAILY_RETRIES


def start_fresh_run():
    state = _load_state()
    state["status"] = "running"
    state["mode"] = "fresh"
    state["started_at"] = _get_current_utc_time()
    state["last_updated"] = _get_current_utc_time()
    state["active_render"] = False
    state["last_error"] = None
    state["retry_count"] = state.get("retry_count", 0) + 1
    _save_state(state)


def set_active_render(is_active: bool):
    state = _load_state()
    state["active_render"] = is_active
    state["last_updated"] = _get_current_utc_time()
    _save_state(state)


def mark_posted(fmt: str = None):
    state = _load_state()
    
    posted_formats = state.get("posted_formats", [])
    if fmt and fmt not in posted_formats:
        posted_formats.append(fmt)
        state["posted_formats"] = posted_formats

    if len(posted_formats) >= 4:
        state["status"] = "posted"
    else:
        # Reset to pending so the next format's time window can trigger!
        state["status"] = "pending"
        
    state["posted_at"] = _get_current_utc_time()
    state["last_updated"] = _get_current_utc_time()
    state["active_render"] = False
    state["last_error"] = None
    _save_state(state)


def mark_failed(error: str):
    state = _load_state()
    state["status"] = "failed"
    state["last_error"] = str(error)
    state["last_updated"] = _get_current_utc_time()
    state["active_render"] = False
    _save_state(state)


def mark_skipped(reason: str = "", fmt: str = None):
    state = _load_state()
    state["status"] = "skipped"
    if reason:
        state["last_error"] = reason
    state["last_updated"] = _get_current_utc_time()
    _save_state(state)


def has_active_nblm_state(memory_dir: str) -> bool:
    """
    Check if any nblm_state_fX.json files exist in memory/.
    These files are written by notebooklm_footage.py when a render task
    is successfully submitted to Google. Their existence means there IS an
    active render pending, regardless of what pipeline_state.json says.
    """
    import glob
    pattern = os.path.join(memory_dir, "nblm_state_f*.json")
    return len(glob.glob(pattern)) > 0
