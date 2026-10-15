import sys, os, argparse
from pathlib import Path
ROOT_DIR = Path("/Users/shameel/Desktop/youtube")
sys.path.insert(0, str(ROOT_DIR))
from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
from uploader.youtube import upload_video
from uploader.instagram import upload_reel
from analytics.tracker import log_upload

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_pos", nargs="?")
    parser.add_argument("--video", dest="video_flag", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--hashtags", nargs="*", default=None)
    args = parser.parse_args()

    v_str = args.video_flag or args.video_pos or str(ROOT_DIR / "output" / "experiments" / "autonomous_characters" / "final" / "short_20261015_004_liya.mp4")
    video_path = Path(v_str).resolve()
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        sys.exit(1)

    title = args.title or "The Dead Body That Tricked Hitler: Operation Mincemeat #shorts"
    description = args.description or ("In 1943, British intelligence won World War Two using a dead body dressed as a fake Royal Marine officer.\nHost Liya breaks down Operation Mincemeat.")
    hashtags = args.hashtags or ["#shorts", "#history", "#military", "#facts", "#didyouknow", "#ww2"]
    ig_caption = f"{title}\n\n{description}\n\n" + " ".join(hashtags)

    print("=" * 60)
    print(f"PUBLISHING: {video_path.name}")
    print(f"TITLE: {title}")
    print("=" * 60)

    try:
        yt_res = upload_video(str(video_path), title, description, hashtags, is_short=True)
        print(f"YouTube URL: {yt_res.get('url')}")
        log_upload(yt_res["video_id"], 1, title, description[:100])
    except Exception as e:
        print(f"YouTube upload error: {e}")

    if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
        try:
            ig_id = upload_reel(str(video_path), ig_caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
            print(f"Instagram Reel ID: {ig_id}")
        except Exception as e:
            print(f"Instagram upload error: {e}")

if __name__ == "__main__":
    main()
