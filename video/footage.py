import os
import random
import requests
from config import PEXELS_API_KEY, TEMP_DIR, VIDEO_WIDTH

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
HEADERS = {"Authorization": PEXELS_API_KEY}

def fetch_footage(keyword: str, duration_needed: float, max_clips: int = 5) -> list[str]:
    print(f"🎬 Searching Pexels for: '{keyword}'")
    clips = _search_pexels(keyword, per_page=15)
    
    if not clips:
        fallbacks = ["technology", "space", "abstract", "data", "futuristic"]
        for fb in fallbacks:
            print(f"   ↳ Trying fallback: '{fb}'")
            clips = _search_pexels(fb, per_page=15)
            if clips:
                break
                
    if not clips:
        print("⚠️  No Pexels footage found, will use generated background.")
        return []
        
    random.shuffle(clips)
    
    downloaded_paths = []
    total_duration = 0.0
    
    for i, clip in enumerate(clips):
        if total_duration >= duration_needed or len(downloaded_paths) >= max_clips:
            break
            
        url = _pick_best_video_file(clip)
        if url:
            filename = f"clip_{len(downloaded_paths)}.mp4"
            path = _download_clip(url, filename)
            if path:
                downloaded_paths.append(path)
                clip_dur = clip.get("duration", 10)
                total_duration += clip_dur
                print(f"   ✅ Downloaded clip {len(downloaded_paths)}: {clip_dur}s (total: {total_duration:.0f}s)")
                
    return downloaded_paths

def _search_pexels(keyword: str, per_page: int = 15) -> list:
    params = {"query": keyword, "per_page": per_page, "orientation": "portrait", "size": "medium"}
    try:
        resp = requests.get(PEXELS_VIDEO_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("videos", [])
    except Exception:
        return []

def _pick_best_video_file(clip: dict) -> str | None:
    files = clip.get("video_files", [])
    
    # Filter portrait
    vertical_files = [f for f in files if f.get("width", 0) < f.get("height", 0)]
    
    if not vertical_files:
        vertical_files = files # Fallback if no explicit vertical
        
    if not vertical_files:
        return None
        
    # Prefer hd or sd
    preferred = [f for f in vertical_files if f.get("quality") in ["hd", "sd"]]
    if not preferred:
        preferred = vertical_files
        
    # Sort by closest to 1080
    preferred.sort(key=lambda x: abs(x.get("width", 0) - VIDEO_WIDTH))
    
    return preferred[0].get("link") if preferred else None

def _download_clip(url: str, filename: str) -> str | None:
    path = os.path.join(TEMP_DIR, filename)
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return path
    except Exception:
        return None
