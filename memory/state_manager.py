import os
import json
from datetime import datetime, timezone

STATE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory", "pipeline_state.json"))

def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            # Check for day rollover
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
        "status": "pending",  # pending, running, posted, failed, skipped
        "mode": None,         # fresh, resume
        "started_at": None,
        "posted_at": None,
        "last_updated": _get_current_utc_time(),
        "active_render": False,
        "last_error": None
    }

def get_state() -> dict:
    return _load_state()

def start_fresh_run():
    state = _load_state()
    state["status"] = "running"
    state["mode"] = "fresh"
    state["started_at"] = _get_current_utc_time()
    state["last_updated"] = _get_current_utc_time()
    state["active_render"] = False
    state["last_error"] = None
    _save_state(state)

def set_active_render(is_active: bool):
    state = _load_state()
    state["active_render"] = is_active
    state["last_updated"] = _get_current_utc_time()
    _save_state(state)

def mark_posted():
    state = _load_state()
    state["status"] = "posted"
    state["posted_at"] = _get_current_utc_time()
    state["last_updated"] = _get_current_utc_time()
    state["active_render"] = False
    _save_state(state)

def mark_failed(error: str):
    state = _load_state()
    state["status"] = "failed"
    state["last_error"] = str(error)
    state["last_updated"] = _get_current_utc_time()
    _save_state(state)

def mark_skipped(reason: str = ""):
    state = _load_state()
    state["status"] = "skipped"
    if reason:
        state["last_error"] = reason  # Just record why it was skipped
    state["last_updated"] = _get_current_utc_time()
    _save_state(state)
