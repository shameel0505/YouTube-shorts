import os
import json
from datetime import datetime, timedelta, timezone

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "analytics", "performance_log.json"))

def _load_log() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_log(data: list):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def log_upload(video_id: str, fmt: int, topic: str, hook: str):
    data = _load_log()
    now = datetime.now(timezone.utc)
    check_time = now + timedelta(hours=24)
    
    entry = {
        "video_id": video_id,
        "format": fmt,
        "topic": topic,
        "hook": hook,
        "upload_time": now.isoformat(),
        "check_time": check_time.isoformat(),
        "metrics_retrieved": False,
        "views": 0,
        "likes": 0,
        "comments": 0
    }
    data.append(entry)
    _save_log(data)
    print(f"📊 Analytics tracker: Logged upload for video {video_id}. Scheduled check at {check_time.isoformat()}")

def was_format_uploaded_today(fmt: int) -> bool:
    data = _load_log()
    now = datetime.now(timezone.utc).date()
    for entry in reversed(data):
        if entry.get("format") == fmt:
            try:
                dt = datetime.fromisoformat(entry["upload_time"]).date()
                if dt == now:
                    return True
            except Exception:
                pass
    return False

def check_performance():
    from uploader.youtube import _get_youtube_client
    
    print("📈 Checking 24-hour performance metrics...")
    data = _load_log()
    now = datetime.now(timezone.utc)
    
    pending_entries = []
    for entry in data:
        if not entry.get("metrics_retrieved"):
            try:
                dt = datetime.fromisoformat(entry["check_time"])
                if now >= dt:
                    pending_entries.append(entry)
            except Exception:
                pass
                
    if not pending_entries:
        print("   No videos are due for a 24-hour check.")
        return
        
    try:
        youtube = _get_youtube_client()
        video_ids = ",".join([e["video_id"] for e in pending_entries])
        
        resp = youtube.videos().list(
            part="statistics",
            id=video_ids
        ).execute()
        
        stats_map = {}
        for item in resp.get("items", []):
            stats_map[item["id"]] = item.get("statistics", {})
            
        for entry in pending_entries:
            vid = entry["video_id"]
            if vid in stats_map:
                stats = stats_map[vid]
                entry["views"] = int(stats.get("viewCount", 0))
                entry["likes"] = int(stats.get("likeCount", 0))
                entry["comments"] = int(stats.get("commentCount", 0))
                entry["metrics_retrieved"] = True
                print(f"   ✅ [F{entry['format']}] '{entry['topic']}': {entry['views']} views, {entry['likes']} likes")
                
        _save_log(data)
        
        # Determine best performing format historically
        format_views = {1: [], 2: [], 3: [], 4: [], 5: []}
        for entry in data:
            fmt = entry.get("format")
            v = entry.get("views", 0)
            if fmt in format_views and v > 0:
                format_views[fmt].append(v)
                
        print("\n🏆 Historical Performance Summary (Avg Views):")
        for fmt, views in format_views.items():
            if views:
                avg = sum(views) / len(views)
                print(f"   Format {fmt}: {avg:.1f} avg views")
            else:
                print(f"   Format {fmt}: No data yet")
                
    except Exception as e:
        print(f"⚠️ Failed to check performance: {e}")

if __name__ == "__main__":
    check_performance()
