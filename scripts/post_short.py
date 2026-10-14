"""
Publish Short to YouTube and Instagram Reels.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
from uploader.youtube import upload_video
from uploader.instagram import upload_reel
from analytics.tracker import log_upload

def main():
    video_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DIR / "output" / "experiments" / "autonomous_characters" / "final" / "short_20261014_001_liya.mp4"
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)

    title = "Why Pure Water Won't Shock You ⚡ #shorts"
    description = (
        "Did you know that perfectly pure water is actually an electrical insulator?\n"
        "Host Liya breaks down the physics of electrical conductivity in liquids and why mineral ions make all the difference."
    )
    hashtags = ["#shorts", "#science", "#facts", "#didyouknow", "#physics", "#education"]
    ig_caption = f"{title}\n\n{description}\n\n" + " ".join(hashtags)

    print("=" * 65)
    print("🚀 PUBLISHING SHORT TO YOUTUBE & INSTAGRAM")
    print(f"   Video: {video_path.name} ({video_path.stat().st_size / (1024*1024):.2f} MB)")
    print(f"   Title: {title}")
    print("=" * 65)

    yt_result = None
    ig_result = None

    # 1. YouTube Upload
    print("\n▶️ [1/2] Uploading to YouTube Shorts (Public)...")
    try:
        yt_result = upload_video(
            video_path=str(video_path),
            title=title,
            description=description,
            hashtags=hashtags,
            is_short=True
        )
        print(f"   ✅ YouTube Short Live: {yt_result['url']}")
        log_upload(
            video_id=yt_result["video_id"],
            fmt=1,
            topic="Why Pure Water Won't Shock You",
            hook="Did you know that perfectly pure water is actually an electrical insulator?"
        )
    except Exception as e:
        print(f"   ❌ YouTube upload failed: {e}")

    # 2. Instagram Reels Upload
    print("\n📸 [2/2] Uploading to Instagram Reels...")
    if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
        try:
            ig_post_id = upload_reel(
                video_path=str(video_path),
                caption=ig_caption,
                access_token=IG_ACCESS_TOKEN,
                account_id=IG_ACCOUNT_ID
            )
            ig_result = {"post_id": ig_post_id, "url": f"https://www.instagram.com/reel/{ig_post_id}/"}
            print(f"   ✅ Instagram Reel Live! ID: {ig_post_id}")
        except Exception as e:
            print(f"   ❌ Instagram Reels upload failed: {e}")
    else:
        print("   ⚠️ Instagram credentials not found in environment, skipping.")

    print("\n" + "=" * 65)
    print("🎉 PUBLISHING SUMMARY")
    if yt_result:
        print(f"   ▶️ YouTube Short:    {yt_result['url']}")
    if ig_result:
        print(f"   📸 Instagram Reels:  ID {ig_result['post_id']}")
    print("=" * 65)

if __name__ == "__main__":
    main()
