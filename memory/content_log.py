import os
import json
from datetime import datetime, timedelta
from config import TEMP_DIR

LOG_FILE = os.path.join(TEMP_DIR, "../memory/used_topics.json")

def _load_log() -> dict:
    if not os.path.exists(LOG_FILE):
        return {"format1_topics": [], "format2_titles": [], "format3_dilemmas": []}
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            # Ensure keys exist
            for k in ["format1_topics", "format2_titles", "format3_dilemmas"]:
                if k not in data:
                    data[k] = []
            return data
    except Exception:
        return {"format1_topics": [], "format2_titles": [], "format3_dilemmas": []}

def _save_log(data: dict):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def purge_old_entries():
    """Removes F1 and F3 entries older than 90 days."""
    data = _load_log()
    now = datetime.now()
    
    for k in ["format1_topics", "format3_dilemmas"]:
        new_list = []
        for entry in data[k]:
            try:
                dt = datetime.fromisoformat(entry["date"])
                if (now - dt).days <= 90:
                    new_list.append(entry)
            except Exception:
                pass
        data[k] = new_list
        
    _save_log(data)

def is_topic_used(topic: str, fmt: int) -> bool:
    data = _load_log()
    topic = topic.strip().lower()
    
    if fmt == 1:
        for t in data["format1_topics"]:
            if t["text"].strip().lower() == topic:
                return True
    elif fmt == 2:
        for t in data["format2_titles"]:
            if t["text"].strip().lower() == topic:
                return True
    elif fmt == 3:
        now = datetime.now()
        for t in data["format3_dilemmas"]:
            if t["text"].strip().lower() == topic:
                # 60 day lockout for F3
                try:
                    dt = datetime.fromisoformat(t["date"])
                    if (now - dt).days < 60:
                        return True
                except:
                    return True
    return False

def add_used_topic(topic: str, fmt: int):
    data = _load_log()
    entry = {"text": topic, "date": datetime.now().isoformat()}
    
    if fmt == 1:
        data["format1_topics"].append(entry)
    elif fmt == 2:
        data["format2_titles"].append(entry)
    elif fmt == 3:
        data["format3_dilemmas"].append(entry)
        
    _save_log(data)
