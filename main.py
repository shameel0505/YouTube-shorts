import argparse
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

from config import NICHE, TEMP_DIR
from generator.researcher import research_topic
from generator.script import generate_script
from generator.voiceover import generate_voiceover
from video.footage import fetch_footage
from video.captions import transcribe_audio
from video.editor import build_video
from uploader.youtube import upload_short

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    with open("./logs/pipeline.log", "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def clean_temp():
    for f in Path(TEMP_DIR).glob("*"):
        if f.name == "used_topics.json":
            continue
        try:
            f.unlink()
        except Exception:
            pass

def run_pipeline(upload: bool = True, niche: str = None) -> dict:
    try:
        log("━" * 50)
        log(f"🚀 Starting pipeline | niche: {niche or NICHE} | upload: {upload}")
        clean_temp()
        
        log("🔍 Step 1/7: Researching trending topics...")
        research = research_topic(niche=niche)
        log(f"   Chosen topic: {research.get('chosen_topic')}")
        log(f"   Hook angle: {research.get('hook_angle')}")
        log(f"   Sources: {', '.join(research.get('sources_used', []))}")
        
        log("📝 Step 2/7: Generating script from research...")
        script_data = generate_script(niche=niche, research=research)
        log(f"   Title: {script_data['title']}")
        log(f"   Preview: {script_data.get('hook_preview')}")
        with open(os.path.join(TEMP_DIR, "script.json"), "w", encoding="utf-8") as f:
            json.dump(script_data, f)
            
        log("🎙️  Step 3/7: Generating voiceover...")
        audio_path, audio_duration = generate_voiceover(script_data["script"], output_filename="voiceover.mp3")
        log(f"   Duration: {audio_duration:.1f}s")
        
        log("🎬 Step 4/7: Fetching background footage...")
        footage_paths = fetch_footage(keyword=script_data["pexels_keyword"], duration_needed=audio_duration + 2)
        log(f"   Clips found: {len(footage_paths)}")
        
        log("📄 Step 5/7: Generating captions...")
        captions = transcribe_audio(audio_path, words_per_caption=4)
        log(f"   Chunks generated: {len(captions)}")
        
        log("🎞️  Step 6/7: Assembling video...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"short_{timestamp}.mp4"
        video_path = build_video(footage_paths, audio_path, captions, audio_duration, output_filename)
        log(f"   Saved to: {video_path}")
        
        if upload:
            log("📤 Step 7/7: Uploading to YouTube...")
            yt_result = upload_short(video_path, script_data["title"], script_data["description"], script_data["hashtags"])
            log(f"   ✅ Live: {yt_result['url']}")
            result = yt_result
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)")
            log(f"   Video ready at: {video_path}")
            result = {"video_path": video_path}
            
        log("🎉 Pipeline completed successfully!")
        
        return {
            "research": research,
            "script": script_data,
            "audio_duration": audio_duration,
            "video_path": video_path,
            "upload_result": result if upload else None
        }
        
    except Exception as e:
        log(f"❌ Pipeline failed: {e}")
        log(traceback.format_exc())
        raise

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        func=lambda: run_pipeline(upload=True),
        trigger="cron",
        hour=9, minute=0,
        id="daily_short",
        name="Daily YouTube Short",
        misfire_grace_time=3600,
    )
    log("⏰ Scheduler started — posting daily at 09:00 UTC")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler stopped.")

def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Bot")
    parser.add_argument("mode", choices=["run", "dry-run", "schedule", "test-script", "test-voice"], default="run", nargs="?")
    parser.add_argument("--niche", type=str, help="Override NICHE from .env")
    parser.add_argument("--count", type=int, default=1, help="Number of times to run the pipeline")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if args.mode == "test-script":
        research = research_topic(niche=args.niche)
        data = generate_script(niche=args.niche, research=research)
        print("\n" + "═" * 60)
        print(f"TITLE:    {data['title']}")
        print(f"TOPIC:    {data['topic']}")
        print(f"HOOK:     {data.get('hook_preview')}")
        print(f"TAGS:     {' '.join(data['hashtags'])}")
        print(f"PEXELS:   {data['pexels_keyword']}")
        print(f"\nRESEARCH: {research['chosen_topic']}")
        print(f"WHY:      {research['why_viral']}")
        print("\nSCRIPT:\n" + data["script"])
        
    elif args.mode == "test-voice":
        research = research_topic(niche=args.niche)
        data = generate_script(niche=args.niche, research=research)
        path, dur = generate_voiceover(data["script"])
        print(f"\n✅ Voice file: {path} ({dur:.1f}s)")
        
    elif args.mode == "dry-run":
        for i in range(args.count):
            if args.count > 1: print(f"\n--- Dry run {i+1}/{args.count} ---")
            run_pipeline(upload=False, niche=args.niche)
            
    elif args.mode == "schedule":
        run_scheduler()
        
    else:  # run
        for i in range(args.count):
            if args.count > 1: print(f"\n--- Short {i+1}/{args.count} ---")
            run_pipeline(upload=True, niche=args.niche)
