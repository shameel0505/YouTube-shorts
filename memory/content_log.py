import os
import json
from datetime import datetime, timedelta
from config import TEMP_DIR

LOG_FILE = os.path.join(TEMP_DIR, "../memory/used_topics.json")

def _load_log() -> dict:
    if not os.path.exists(LOG_FILE):
        return {"format1_topics": [], "format2_titles": [], "format3_dilemmas": [], "format4_cases": []}
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            # Ensure keys exist
            for k in ["format1_topics", "format2_titles", "format3_dilemmas", "format4_cases"]:
                if k not in data:
                    data[k] = []
            return data
    except Exception:
        return {"format1_topics": [], "format2_titles": [], "format3_dilemmas": [], "format4_cases": []}

def _save_log(data: dict):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def purge_old_entries():
    """Removes F1, F3, and F4 entries older than 90 days."""
    data = _load_log()
    now = datetime.now()
    
    for k in ["format1_topics", "format3_dilemmas", "format4_cases"]:
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

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
    "these", "those", "it", "its", "you", "your", "he", "she", "they", "we", "i", "what",
    "why", "how", "when", "where", "who", "which"
}

def _extract_keywords(text: str) -> set[str]:
    import re
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = [w for w in cleaned.split() if len(w) > 3 and w not in STOPWORDS]
    return set(words)

def _is_similar(text_a: str, text_b: str, threshold: float = 0.45) -> bool:
    """Checks if two topic titles or descriptions share significant content tokens."""
    kw_a = _extract_keywords(text_a)
    kw_b = _extract_keywords(text_b)
    if not kw_a or not kw_b:
        return text_a.strip().lower() == text_b.strip().lower()

    intersection = kw_a.intersection(kw_b)
    overlap = len(intersection) / min(len(kw_a), len(kw_b))
    
    # Critical entity check (e.g., specific names like 'byford', 'slotin', 'daghlian', 'chornobyl')
    critical_entities = {"byford", "dolphin", "slotin", "plutonium", "decompression"}
    if len(intersection.intersection(critical_entities)) >= 1 and len(intersection) >= 2:
        return True

    return overlap >= threshold

def is_topic_used(topic: str, fmt: int) -> bool:
    data = _load_log()
    topic = topic.strip().lower()

    # 1. Check against performance_log.json (actual uploaded YouTube videos)
    perf_log_file = os.path.join(TEMP_DIR, "../analytics/performance_log.json")
    if os.path.exists(perf_log_file):
        try:
            with open(perf_log_file, "r") as f:
                perf_data = json.load(f)
                for entry in perf_data:
                    past_title = entry.get("title", "")
                    if _is_similar(topic, past_title):
                        print(f"🚫 [Deduplication] Topic rejected! Shares keywords with published video: '{past_title}'")
                        return True
        except Exception:
            pass

    # 2. Check format specific logs
    key_map = {
        1: "format1_topics",
        2: "format2_titles",
        3: "format3_dilemmas",
        4: "format4_cases"
    }
    target_key = key_map.get(fmt, "format1_topics")
    
    for t in data.get(target_key, []):
        logged_text = t.get("text", "")
        if _is_similar(topic, logged_text):
            print(f"🚫 [Deduplication] Topic rejected! Overlaps with logged topic: '{logged_text[:60]}...'")
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
    elif fmt == 4:
        data["format4_cases"].append(entry)
        
    _save_log(data)
