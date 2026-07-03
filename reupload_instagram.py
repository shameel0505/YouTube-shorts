import os
import json
import glob
from dotenv import load_dotenv
from uploader.instagram import upload_reel
from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID, TEMP_DIR

def reupload():
    # Reload environment to fetch updated tokens
    load_dotenv(override=True)
    
    token = os.getenv("IG_ACCESS_TOKEN")
    account_id = os.getenv("IG_ACCOUNT_ID")
    
    if not token or not account_id:
        print("❌ Error: IG_ACCESS_TOKEN or IG_ACCOUNT_ID is missing from .env!")
        return
        
    print(f"📸 Instagram Re-uploader starting with Account ID: {account_id}")
    
    # Check and upload files on disk
    formats = [1, 2, 3, 4]
    for fmt in formats:
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"[FORMAT {fmt}] Re-uploading to Instagram...")
        
        # Find script data
        script_file = os.path.join(TEMP_DIR, f"script_f{fmt}.json")
        if not os.path.exists(script_file):
            print(f"⚠️ Script file not found: {script_file}. Skipping.")
            continue
            
        with open(script_file, "r") as f:
            script_data = json.load(f)
            
        # Find video file
        video_files = glob.glob(os.path.join(TEMP_DIR, f"notebooklm_f{fmt}_*.mp4"))
        if not video_files:
            print(f"⚠️ Video file not found for Format {fmt}. Skipping.")
            continue
            
        video_files.sort(key=os.path.getmtime)
        video_path = video_files[-1]
        
        print(f"   Video: {video_path}")
        print(f"   Title: {script_data.get('title')}")
        
        # Build caption
        title = script_data.get("title", "")
        description = script_data.get("description", "")
        hashtags = script_data.get("hashtags", [])
        caption = f"{title}\n\n{description}\n\n" + " ".join(hashtags)
        
        try:
            print("   📸 Uploading to Instagram Reels...")
            post_id = upload_reel(video_path, caption, token, account_id)
            print(f"   ✅ Success! Instagram Post ID: {post_id}")
        except Exception as e:
            print(f"   ❌ IG Upload Failed for Format {fmt}: {e}")

if __name__ == "__main__":
    reupload()
