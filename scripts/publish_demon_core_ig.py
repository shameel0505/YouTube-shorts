import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path("/Users/shameel/Desktop/youtube")
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(override=True)

from uploader.instagram import upload_reel, publish_from_url
from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID

VIDEO_PATH = ROOT_DIR / "output" / "experiments" / "autonomous_characters" / "final" / "short_20261022_004_liya.mp4"
TITLE = "The Screwdriver That Slipped: The Demon Core #shorts"
DESCRIPTION = (
    "In 1946, physicist Louis Slotin controlled a 14-lb subcritical plutonium sphere with a flathead screwdriver. "
    "When the blade slipped 2 millimeters, a blinding flash of blue Cherenkov radiation filled the room. "
    "Host Liya breaks down the Demon Core criticality incident and the reflex that saved 7 colleagues."
)
HASHTAGS = ["#shorts", "#history", "#science", "#facts", "#physics", "#demoncore", "#losalamos", "#educational"]
CAPTION = f"{TITLE}\n\n{DESCRIPTION}\n\n" + " ".join(HASHTAGS)

# Pre-uploaded GCS Signed URL (valid for 7 days)
PUBLIC_URL = "https://storage.googleapis.com/shameel-shorts-free-tier-bucket/video_1792664878.mp4?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=storage-object-admin%40youtube-auto-497707.iam.gserviceaccount.com%2F20261022%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20261022T102805Z&X-Goog-Expires=604800&X-Goog-SignedHeaders=host&X-Goog-Signature=13ccb4910cbaf5e1c3c07615fee6c7602d38bdfdc51a89ab7cfe978669f8ca0b83e6152173f49e4fdf3fed50cba7ee016efec83f2d27adec69de16a7e28b1ce32440c3d8eab1c3cfc8db8d5b55c6840abae8f0e8b022c87b63f6f69c5838aed31e77a37972a1e2e5b89313be4021e5a48f11517fb27ac98dc81a58b099b7f2e5d9589197b0ffe43ed4e5d7d64c88e316270003522bbaca587a5b0fe186d1c2049a6d16131026bfaab9ad015b6fd091007bfaf3a5f1f194cf89be6bb3282770537e0485568fdee093b0909db4116b4728e88744792094bb4c7d9a2cf6281759437440381b830b9a9c357317222902b591880b36470e05511b55cda03fb757664e"

def main():
    print("=" * 60)
    print("PUBLISHING TO INSTAGRAM REELS")
    print(f"Video: {VIDEO_PATH.name}")
    print(f"Title: {TITLE}")
    print("=" * 60)

    token = os.getenv("IG_ACCESS_TOKEN") or IG_ACCESS_TOKEN
    account_id = os.getenv("IG_ACCOUNT_ID") or IG_ACCOUNT_ID

    if not token or not account_id:
        print("❌ Error: Missing IG_ACCESS_TOKEN or IG_ACCOUNT_ID.")
        sys.exit(1)

    try:
        print("📡 Publishing via pre-staged public GCS URL...")
        reel_id = publish_from_url(PUBLIC_URL, CAPTION, token, account_id)
        print(f"✅ Instagram Reel Published! Reel ID: {reel_id}")
    except Exception as e:
        print(f"⚠️ Direct URL publish failed: {e}")
        print("🔄 Falling back to standard multi-provider upload...")
        try:
            reel_id = upload_reel(str(VIDEO_PATH), CAPTION, token, account_id)
            print(f"✅ Instagram Reel Published! Reel ID: {reel_id}")
        except Exception as e2:
            print(f"❌ Instagram publish error: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
