import os
import requests
import random
from config import PEXELS_API_KEY, TEMP_DIR, ASSETS_IMAGES_DIR

def fetch_pexels_images(script_data: dict, count: int = 3) -> list[dict]:
    """Fetches images from Pexels using a combined topic+keyword query."""
    if not PEXELS_API_KEY or not script_data:
        return []
        
    title = script_data.get("title", "").split()[:3]
    topic_prefix = " ".join(title)
    keyword = script_data.get("pexels_keyword", "")
    query = f"{topic_prefix} {keyword}".strip()
    
    print(f"   🔍 Fetching Pexels images for query: {query}")
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params={"query": query, "per_page": count, "orientation": "portrait"},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("photos", [])
    except Exception as e:
        print(f"   ⚠️ Pexels API error: {e}")
    return []

def fetch_brave_images(script_data: dict, count: int = 5) -> list[dict]:
    """Fetches images from Brave API."""
    from config import BRAVE_API_KEY
    if not BRAVE_API_KEY or not script_data:
        return []
        
    title = script_data.get("title", "").split()[:3]
    topic_prefix = " ".join(title)
    keyword = script_data.get("pexels_keyword", "")
    query = f"{topic_prefix} {keyword}".strip()
    
    print(f"   🔍 Fetching Brave images for query: {query}")
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        resp = requests.get(
            "https://api.search.brave.com/res/v1/images/search",
            headers=headers,
            params={"q": query, "count": count},
            timeout=10
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            formatted = []
            for r in results:
                formatted.append({
                    "width": r.get("properties", {}).get("width", 1080),
                    "height": r.get("properties", {}).get("height", 1920),
                    "src": {"large2x": r.get("properties", {}).get("url", "")}
                })
            return formatted
    except Exception as e:
        print(f"   ⚠️ Brave API error: {e}")
    return []

def get_pattern_image(script_data: dict, manual: bool = False) -> str:
    """Returns local path to the selected pattern interrupt image."""
    if manual:
        photos = fetch_brave_images(script_data, count=5)
    else:
        photos = fetch_pexels_images(script_data, count=3)
    
    valid_photos = []
    for p in photos:
        # Pexels images are guaranteed to be high res usually, Brave might return smaller
        if p.get("width", 0) >= 600:
            valid_photos.append(p)
            
    if not valid_photos:
        # Fallback to local
        if os.path.exists(ASSETS_IMAGES_DIR):
            imgs = [f for f in os.listdir(ASSETS_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if imgs:
                chosen = random.choice(imgs)
                return os.path.join(ASSETS_IMAGES_DIR, chosen)
        return None
        
    if manual:
        from telegram.approver import wait_for_image_approval
        selected_photo = wait_for_image_approval(valid_photos)
        if not selected_photo:
            # Timeout, use highest res
            selected_photo = max(valid_photos, key=lambda x: x.get("width", 0) * x.get("height", 0))
    else:
        # Auto mode: highest res
        selected_photo = max(valid_photos, key=lambda x: x.get("width", 0) * x.get("height", 0))
        
    try:
        img_url = selected_photo["src"]["large2x"]
        img_data = requests.get(img_url, timeout=10).content
        tmp_img = os.path.join(TEMP_DIR, "pexels_pattern.jpg")
        with open(tmp_img, "wb") as f:
            f.write(img_data)
        return tmp_img
    except Exception as e:
        print(f"   ⚠️ Image download failed: {e}")
        
    return None
