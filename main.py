"""
main.py
Full pipeline: Script → Voiceover → Footage → Edit → Caption → Upload
Run once manually or schedule with APScheduler / cron.
"""

import os
import sys
import json
import shutil
import argparse
import traceback
from datetime import datetime, timezone
from pathlib import Path

from config import TEMP_DIR, OUTPUT_DIR, NICHE, SHORTS_PER_DAY
from generator.researcher import research_topic
from generator.script    import generate_script
from generator.voiceover import generate_voiceover
from video.footage       import fetch_footage
from video.captions      import transcribe_audio
from video.editor        import build_video
from uploader.youtube    import upload_short, get_next_upload_time


LOG_FILE = "./logs/pipeline.log"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs("./logs", exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def clean_temp():
    """Remove temp files from previous run."""
    for f in Path(TEMP_DIR).glob("*"):
        try:
            f.unlink()
        except Exception:
            pass


def run_pipeline(upload: bool = True, niche: str = None) -> dict:
    """
    Execute the full Short creation and upload pipeline.
    Returns dict with metadata about the created video.
    """
    log("━" * 50)
    log(f"🚀 Starting pipeline | niche: {niche or NICHE} | upload: {upload}")
    clean_temp()

    result = {}

    try:
        # ── Step 1: Research trending topics ────────────────────────────────
        log("🔍 Step 1/7: Researching trending topics...")
        research = research_topic(niche=niche)
        log(f"   Topic:  {research['chosen_topic']}")
        log(f"   Hook:   {research['hook_angle']}")
        log(f"   Sources: {', '.join(research.get('sources_used', []))}")
        result["research"] = research

        # ── Step 2: Generate Script ──────────────────────────────────────────
        log("📝 Step 2/7: Generating script from research...")
        script_data = generate_script(niche=niche, research=research)
        log(f"   Title:   {script_data['title']}")
        log(f"   Hook:    {script_data.get('hook_preview', '')}")
        result["script"] = script_data

        # Save script JSON
        script_path = os.path.join(TEMP_DIR, "script.json")
        with open(script_path, "w") as f:
            json.dump(script_data, f, indent=2)

        # ── Step 3: Generate Voiceover ───────────────────────────────────────
        log("🎙️  Step 3/7: Generating voiceover...")
        audio_path, audio_duration = generate_voiceover(
            script_data["script"],
            output_filename="voiceover.mp3",
        )
        log(f"   Duration: {audio_duration:.1f}s")
        result["audio_duration"] = audio_duration

        # ── Step 4: Download Footage ─────────────────────────────────────────
        log("🎬 Step 4/7: Fetching background footage...")
        footage_paths = fetch_footage(
            keyword=script_data["pexels_keyword"],
            duration_needed=audio_duration + 2,
        )
        log(f"   Got {len(footage_paths)} clips")
        result["footage_clips"] = len(footage_paths)

        # ── Step 5: Transcribe for Captions ─────────────────────────────────
        log("📄 Step 5/7: Generating captions...")
        captions = transcribe_audio(audio_path, words_per_caption=4)
        log(f"   {len(captions)} caption chunks")

        # ── Step 6: Assemble Video ───────────────────────────────────────────
        log("🎞️  Step 6/7: Assembling video...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"short_{timestamp}.mp4"
        video_path = build_video(
            footage_paths=footage_paths,
            audio_path=audio_path,
            captions=captions,
            audio_duration=audio_duration,
            output_filename=output_filename,
        )
        result["video_path"] = video_path
        log(f"   Saved: {video_path}")

        # ── Step 7: Upload to YouTube ────────────────────────────────────────
        if upload:
            log("📤 Step 7/7: Uploading to YouTube...")
            yt_result = upload_short(
                video_path=video_path,
                title=script_data["title"],
                description=script_data["description"],
                hashtags=script_data["hashtags"],
            )
            result["youtube"] = yt_result
            log(f"   ✅ Live: {yt_result['url']}")
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)")
            log(f"   Video ready at: {video_path}")

        log("🎉 Pipeline completed successfully!")
        return result

    except Exception as e:
        log(f"❌ Pipeline failed: {e}")
        log(traceback.format_exc())
        raise


def run_scheduler():
    """Run the bot on a daily schedule using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="UTC")

    # Schedule at 9:00 AM UTC daily (good time for global reach)
    scheduler.add_job(
        func=lambda: run_pipeline(upload=True),
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_short",
        name="Daily YouTube Short",
        misfire_grace_time=3600,
    )

    log("⏰ Scheduler started — posting daily at 09:00 UTC")
    log("   Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler stopped.")


def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Shorts Bot")
    parser.add_argument(
        "mode",
        nargs="?",
        default="run",
        choices=["run", "dry-run", "schedule", "test-script", "test-voice"],
        help=(
            "run         = full pipeline + upload\n"
            "dry-run     = full pipeline, no upload\n"
            "schedule    = start daily scheduler\n"
            "test-script = generate + print script only\n"
            "test-voice  = generate script + voice only\n"
        ),
    )
    parser.add_argument("--niche", type=str, default=None, help="Override niche from .env")
    parser.add_argument("--count", type=int, default=1, help="Number of shorts to produce")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.mode == "test-script":
        data = generate_script(niche=args.niche)
        print("\n" + "═" * 60)
        print(f"TITLE:   {data['title']}")
        print(f"TOPIC:   {data['topic']}")
        print(f"HOOK:    {data.get('hook_preview')}")
        print(f"TAGS:    {' '.join(data['hashtags'])}")
        print(f"PEXELS:  {data['pexels_keyword']}")
        print("\nSCRIPT:\n" + data["script"])

    elif args.mode == "test-voice":
        data = generate_script(niche=args.niche)
        path, dur = generate_voiceover(data["script"])
        print(f"\n✅ Voice file: {path} ({dur:.1f}s)")

    elif args.mode == "dry-run":
        for i in range(args.count):
            print(f"\n--- Dry run {i+1}/{args.count} ---")
            run_pipeline(upload=False, niche=args.niche)

    elif args.mode == "schedule":
        run_scheduler()

    else:  # run
        for i in range(args.count):
            if args.count > 1:
                print(f"\n--- Short {i+1}/{args.count} ---")
            run_pipeline(upload=True, niche=args.niche)
