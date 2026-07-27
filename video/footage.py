import os
import random
from config import GAMEPLAY_DIR

def fetch_footage(keyword: str = None, duration_needed: float = 0.0, fmt: int = 1) -> list[str]:
    print(f"🎬 Selecting background gameplay footage for format {fmt}...")
    
    if not os.path.exists(GAMEPLAY_DIR):
        raise RuntimeError("Gameplay directory not found! Please run setup_gameplay.sh")
        
    subfolder_map = {
        1: ["facts", "satisfying", "timelapse"],
        2: ["thriller", "underwater"],
        3: ["dilemma", "timelapse", "satisfying"]
    }
    
    allowed_subs = subfolder_map.get(fmt, [])
    clips = []
    
    # Gather clips from all existing/populated allowed subfolders
    for sub in allowed_subs:
        target_dir = os.path.join(GAMEPLAY_DIR, sub)
        if os.path.exists(target_dir):
            sub_clips = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".mp4")]
            clips.extend(sub_clips)
            
    # Fallback to root if all subfolders are empty/missing
    if not clips:
        clips = [os.path.join(GAMEPLAY_DIR, f) for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    
    if not clips:
        print("   ⚠️ No gameplay MP4 files found in the gameplay directory. B-roll fallback skipped.")
        return []
        
    chosen = random.choice(clips)
    print(f"   ✅ Selected: {os.path.basename(chosen)}")
    return [chosen]
