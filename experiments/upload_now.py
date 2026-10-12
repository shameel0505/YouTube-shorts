import os
import sys

# Add parent dir to path to import config and uploader from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
from uploader.youtube import upload_video
from uploader.instagram import upload_reel

video_path = "/Users/shameel/Downloads/How_Exploding_Stars_Forged_Your_Body.mp4"
title = "How Exploding Stars Forged Your Body 🌟 #shorts"
description = "Every atom in your body came from a star that exploded billions of years ago. You are literally made of stardust! 💫✨\n\n#space #science #astronomy #stardust #supernova #facts #mindblowing #shorts #universe #education"
hashtags = ["space", "science", "astronomy", "stardust", "supernova", "facts", "mindblowing", "shorts", "universe", "education"]
ig_caption = "Every atom in your body came from a star that exploded billions of years ago. You are literally made of stardust! 💫✨\n\n#space #science #astronomy #stardust #supernova #facts #mindblowing #universe #education"

print("🚀 Starting YouTube upload...")
try:
    # Set schedule_time to None to publish immediately
    yt_result = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        hashtags=hashtags,
        schedule_time=None, 
        is_short=True
    )
    print(f"✅ YouTube Upload Success: {yt_result}")
except Exception as e:
    print(f"❌ YouTube Upload Failed: {e}")

print("\n🚀 Starting Instagram upload...")
try:
    if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
        ig_result = upload_reel(
            video_path=video_path,
            caption=ig_caption,
            access_token=IG_ACCESS_TOKEN,
            account_id=IG_ACCOUNT_ID
        )
        print(f"✅ Instagram Upload Success: {ig_result}")
    else:
        print("❌ Instagram Upload Failed: IG_ACCESS_TOKEN or IG_ACCOUNT_ID not found in config.")
except Exception as e:
    print(f"❌ Instagram Upload Failed: {e}")
