"""
YouTube Shorts Automation Bot
Supports three daily video formats:
  Format 1 — Mind-Blowing Facts     (daily at FORMAT1_SCHEDULE_HOUR UTC)
  Format 2 — Serialized Thriller    (daily at FORMAT2_SCHEDULE_HOUR UTC)
  Format 3 — Moral Dilemma          (daily at FORMAT3_SCHEDULE_HOUR UTC)

Usage:
  python main.py run        --format 1|2|3|all
  python main.py dry-run    --format 1|2|3|all
  python main.py schedule
  python main.py test-script --format 1|2|3
  python main.py test-voice  --format 1|2|3
"""
import argparse
import os
import json
import traceback
import time
from datetime import datetime
from pathlib import Path

import pydub

from config import (
    NICHE, TEMP_DIR,
    FORMAT1_SCHEDULE_HOUR, FORMAT2_SCHEDULE_HOUR, FORMAT3_SCHEDULE_HOUR,
)
from generator.researcher import research_topic, research_thriller, research_dilemma
from generator.script import generate_script, generate_thriller, generate_dilemma
from generator.voiceover import generate_voiceover
from generator.story_state import load_state, save_state, reset_state
from video.footage import fetch_footage
from video.captions import transcribe_audio
from video.editor import build_video
from uploader.youtube import upload_short
from uploader.instagram import upload_reel
import quota_tracker


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str, fmt: str = ""):
    ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[FORMAT {fmt}] " if fmt else ""
    line   = f"[{ts}] {prefix}{msg}"
    print(line)
    try:
        with open("./logs/pipeline.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _clean_temp_for_format(fmt_num: int):
    """Remove temp files for one format without touching files for other formats."""
    suffix = f"_f{fmt_num}"
    for p in Path(TEMP_DIR).glob("*"):
        name = p.name
        # Skip permanent state files
        if name in ("used_topics.json", "gemini_quota.json", "story_state.json"):
            continue
        if suffix in name:
            try:
                p.unlink()
            except Exception:
                pass


def _load_audio_duration(path: str) -> float:
    try:
        return len(pydub.AudioSegment.from_mp3(path)) / 1000.0
    except Exception:
        return 0.0


# ── FORMAT 1: Mind-Blowing Facts ─────────────────────────────────────────────

def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False) -> dict:
    fmt = "1"
    log("━" * 50, fmt)
    
    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(1):
            log("⏭️  Format 1 already uploaded today. Skipping.", fmt)
            return {"format": 1, "skipped": True}

    log(f"🚀 Starting | niche: {niche or NICHE} | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(1)

    script_path  = os.path.join(TEMP_DIR, "script_f1.json")
    caption_path = os.path.join(TEMP_DIR, "captions_f1.json")
    voice_path   = os.path.join(TEMP_DIR, "voiceover_f1.mp3")

    try:
        # Steps 1 & 2 — Research + Script
        script_data = None
        if os.path.exists(script_path):
            with open(script_path) as f:
                cached_data = json.load(f)
            from memory.content_log import is_topic_used
            if is_topic_used(cached_data.get("chosen_topic", ""), 1):
                log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                _clean_temp_for_format(1)
            else:
                log("📝 Steps 1 & 2: Loading cached script...", fmt)
                script_data = cached_data
                research = {"chosen_topic": script_data.get("chosen_topic", "Cached")}
                
        if not script_data:
            if not upload:
                log("🧪 Dry run: Using static mock script for Format 1...", fmt)
                script_data = {
                    "title": "Static F1 Dry Run",
                    "description": "Dry run description",
                    "hashtags": ["#shorts"],
                    "script": "Did you know that water can boil and freeze at the exact same time? It's called the triple point, and it happens when temperature and pressure are perfectly balanced.",
                    "hook": "Boil and freeze at the same time",
                    "pexels_keyword": "iceberg",
                    "chosen_topic": "Triple point of water",
                    "hook_angle": "Scientific impossibility"
                }
            else:
                if not quota_tracker.can_proceed(2):
                    raise RuntimeError("Gemini quota exhausted — Format 1 skipped.")
                log("🔍 Step 1/7: Researching trending topics...", fmt)
                research_list = research_topic(niche=niche)
                
                if manual:
                    from telegram.approver import wait_for_topic_approval
                    topic = wait_for_topic_approval(research_list)
                else:
                    topic = research_list[0] if isinstance(research_list, list) else research_list
                    
                log(f"   Topic: {topic.get('text')}", fmt)
                log(f"   {quota_tracker.status()}", fmt)

                log("📝 Step 2/7: Generating script...", fmt)
                script_data = generate_script(niche=niche, research=topic)
                script_data["chosen_topic"] = topic.get("text") or topic.get("chosen_topic") or "Manual Topic"
                script_data["hook_angle"] = topic.get("source") or topic.get("hook_angle") or "Unknown"
                
                log(f"   Title: {script_data['title']}", fmt)
                log(f"   Hook preview: {script_data.get('hook_preview', '')[:80]}", fmt)
                log(f"   {quota_tracker.status()}", fmt)
            with open(script_path, "w") as f:
                json.dump(script_data, f)

        # Step 3 — Voiceover
        if os.path.exists(voice_path):
            log("🎙️  Step 3/7: Loading cached voiceover...", fmt)
            audio_path     = voice_path
            audio_duration = _load_audio_duration(audio_path)
        else:
            log("🎙️  Step 3/7: Generating voiceover via Kokoro...", fmt)
            audio_path, audio_duration = generate_voiceover(
                script_data["script"], output_filename="voiceover_f1.mp3"
            )
        log(f"   Duration: {audio_duration:.1f}s", fmt)

        # Step 4 — Footage
        existing_clips = sorted(Path(TEMP_DIR).glob("clip_f1_*.mp4"))
        if existing_clips:
            log("🎬 Step 4/7: Using cached footage...", fmt)
            footage_paths = [str(p) for p in existing_clips]
        else:
            log("🎬 Step 4/7: Selecting gameplay footage...", fmt)
            footage_paths = fetch_footage(
                keyword=script_data.get("pexels_keyword", ""),
                duration_needed=audio_duration + 2,
                fmt=1
            )
        log(f"   Clips: {len(footage_paths)}", fmt)

        # Step 5 — Captions
        if os.path.exists(caption_path):
            log("📄 Step 5/7: Loading cached captions...", fmt)
            with open(caption_path) as f:
                captions = json.load(f)
        else:
            log("📄 Step 5/7: Transcribing captions...", fmt)
            captions = transcribe_audio(audio_path, words_per_caption=3)
            with open(caption_path, "w") as f:
                json.dump(captions, f)
        log(f"   Chunks: {len(captions)}", fmt)

        # Step 6 — Render
        log("🎞️  Step 6/7: Assembling video...", fmt)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        from video.pexels import get_pattern_image
        pattern_img_path = get_pattern_image(script_data, manual=manual)
        
        video_path = build_video(
            footage_paths, audio_path, captions, audio_duration,
            f"short_f1_{ts}.mp4",
            fmt=1, script_data=script_data, pattern_img_path=pattern_img_path
        )
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            log("📤 Step 7/7: Uploading to YouTube...", fmt)
            result = upload_short(
                video_path, script_data["title"],
                script_data["description"], script_data["hashtags"],
            )
            log(f"   ✅ YouTube Live: {result['url']}", fmt)
            
            from analytics.tracker import log_upload
            from memory.content_log import add_used_topic
            if "video_id" in result:
                log_upload(result["video_id"], 1, script_data["chosen_topic"], script_data["hook_angle"])
            add_used_topic(script_data["chosen_topic"], 1)
            
            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                try:
                    log("📸 Uploading to Instagram Reels...", fmt)
                    caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                    ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                    result["ig_post_id"] = ig_post_id
                except Exception as e:
                    log(f"   ⚠️ IG Upload Failed: {e}", fmt)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        log("🎉 Format 1 completed successfully!", fmt)
        return {"format": 1, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        log(f"❌ Format 1 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


# ── FORMAT 2: Serialized Thriller ─────────────────────────────────────────────

def run_format2(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False) -> dict:
    from generator.story_state import load_state, save_state, reset_state, is_story_abandoned, start_new_story, archive_completed_story
    from generator.script import generate_thriller
    from generator.researcher import research_thriller
    
    fmt = "2"
    log("━" * 50, fmt)
    
    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(2):
            log("⏭️  Format 2 already uploaded today. Skipping.", fmt)
            return {"format": 2, "skipped": True}

    if attempt == 1 and not resume:
        _clean_temp_for_format(2)

    script_path = os.path.join(TEMP_DIR, "script_f2.json")

    try:
        story_state = load_state()
        
        needs_new_story = (
            not story_state.get("parts_scripts") or 
            is_story_abandoned(story_state) or 
            story_state.get("story_complete")
        )
        
        if needs_new_story:
            if story_state.get("story_complete"):
                archive_completed_story(story_state)
            else:
                log("⚠️ Previous story abandoned. Starting fresh.", fmt)
                
            log("🔄 Starting a fresh 7-part story arc...", fmt)
            if not upload:
                log("🧪 Dry run: Using static mock arc for Format 2...", fmt)
                arc_data = {
                    "story_title": "The Simulation Glitch",
                    "story_premise": "A programmer finds a bug in reality.",
                    "total_parts": 7,
                    "parts": [
                        {
                            "part_number": i,
                            "script_text": f"Alex stared at the screen. The code was bleeding into the real world. A shadow detached from the wall and moved toward him. He tried to scream, but the air turned to static. The simulation was collapsing.",
                            "cliffhanger_summary": "A shadow attacks.",
                            "recap_line": f"Previously, the code bled into reality." if i > 1 else ""
                        } for i in range(1, 8)
                    ]
                }
            else:
                research = research_thriller()
                arc_data = generate_thriller(research=research)
            story_state = start_new_story(arc_data)
            save_state(story_state)
            
        current_part = story_state.get("current_part", 1)
        part_index = current_part - 1
        
        log(f"🚀 Starting Serialized Thriller Part {current_part} | upload: {upload} | attempt: {attempt}", fmt)
        
        caption_path = os.path.join(TEMP_DIR, f"captions_f2_p{current_part}.json")
        voice_path   = os.path.join(TEMP_DIR, f"voiceover_f2_p{current_part}.mp3")
        
        # Get the script for the current part
        part_script_obj = story_state["parts_scripts"][part_index]
        base_script = part_script_obj["script_text"]
        
        final_script = base_script
        
        # 1. Add recap if not part 1
        if current_part > 1:
            prev_recap = story_state["parts_scripts"][part_index - 1].get("recap_line", "")
            if prev_recap:
                final_script = f"{prev_recap} {final_script}"
                
        # 2. Add come back tomorrow if not final part
        if current_part < story_state["total_parts"]:
            final_script = f"{final_script} Come back tomorrow for the next part."
            
        script_data = {
            "title": f"{story_state['story_title']} - Part {current_part}",
            "description": f"Part {current_part} of {story_state['story_title']}. {story_state['story_premise']}",
            "hashtags": ["#shorts", "#thriller", "#storytime"],
            "script": final_script,
            "hook": story_state['story_title'],
            "part": current_part
        }
        
        with open(script_path, "w") as f:
            json.dump(script_data, f)

        # Step 3 — Voiceover
        if os.path.exists(voice_path):
            log("🎙️  Step 3/7: Loading cached voiceover...", fmt)
            audio_path     = voice_path
            audio_duration = _load_audio_duration(audio_path)
        else:
            log("🎙️  Step 3/7: Generating voiceover via Kokoro...", fmt)
            audio_path, audio_duration = generate_voiceover(
                script_data["script"], output_filename="voiceover_f2.mp3"
            )
        log(f"   Duration: {audio_duration:.1f}s", fmt)

        # Step 4 — Footage
        log("🎬 Step 4/7: Selecting gameplay footage...", fmt)
        footage_paths = fetch_footage(duration_needed=audio_duration + 2, fmt=2)
        log(f"   Clips: {len(footage_paths)}", fmt)

        # Step 5 — Captions
        if os.path.exists(caption_path):
            log("📄 Step 5/7: Loading cached captions...", fmt)
            with open(caption_path) as f:
                captions = json.load(f)
        else:
            log("📄 Step 5/7: Transcribing captions...", fmt)
            captions = transcribe_audio(audio_path, words_per_caption=3)
            with open(caption_path, "w") as f:
                json.dump(captions, f)
        log(f"   Chunks: {len(captions)}", fmt)

        # Step 6 — Render
        log("🎞️  Step 6/7: Assembling video...", fmt)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = build_video(
            footage_paths, audio_path, captions, audio_duration,
            f"short_f2_{ts}.mp4",
            fmt=2, script_data=script_data
        )
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            log("📤 Step 7/7: Uploading to YouTube...", fmt)
            result = upload_short(
                video_path, script_data["title"],
                script_data["description"], script_data["hashtags"],
            )
            log(f"   ✅ Live: {result['url']}", fmt)
            
            # Post-upload tracking
            from analytics.tracker import log_upload
            if "video_id" in result:
                log_upload(result["video_id"], 2, story_state["story_title"], script_data["hook"])
            
            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                try:
                    log("📸 Uploading to Instagram Reels...", fmt)
                    caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                    ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                    result["ig_post_id"] = ig_post_id
                except Exception as e:
                    log(f"   ⚠️ IG Upload Failed: {e}", fmt)
                
            story_state["parts_posted"][part_index] = True
            if current_part >= story_state["total_parts"]:
                story_state["story_complete"] = True
                log("🎉 Story arc fully completed!", fmt)
            else:
                story_state["current_part"] = current_part + 1
            save_state(story_state)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        log("🎉 Format 2 completed successfully!", fmt)
        return {"format": 2, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        log(f"❌ Format 2 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

def run_format3(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False) -> dict:
    fmt = "3"
    log("━" * 50, fmt)
    
    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(3):
            log("⏭️  Format 3 already uploaded today. Skipping.", fmt)
            return {"format": 3, "skipped": True}

    log(f"🚀 Starting Moral Dilemma | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(3)

    script_path  = os.path.join(TEMP_DIR, "script_f3.json")
    caption_path = os.path.join(TEMP_DIR, "captions_f3.json")
    voice_path   = os.path.join(TEMP_DIR, "voiceover_f3.mp3")

    try:
        # Steps 1 & 2 — Research + Script
        script_data = None
        if os.path.exists(script_path):
            with open(script_path) as f:
                cached_data = json.load(f)
            from memory.content_log import is_topic_used
            if is_topic_used(cached_data.get("dilemma_seed", ""), 3):
                log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                _clean_temp_for_format(3)
            else:
                log("📝 Steps 1 & 2: Loading cached dilemma script...", fmt)
                script_data = cached_data
                
        if not script_data:
            if not upload:
                log("🧪 Dry run: Using static mock script for Format 3...", fmt)
                script_data = {
                    "title": "The Million Dollar Button",
                    "description": "Would you press it?",
                    "hashtags": ["#shorts", "#dilemma"],
                    "script": "There is a button in front of you. If you press it, you receive one million dollars, but a random person in the world loses all their memories. You have five seconds to decide.",
                    "hook": "The million dollar button",
                    "closing_question": "Would you press the button?",
                    "dilemma_seed": "Memory wipe for money"
                }
            else:
                if not quota_tracker.can_proceed(2):
                    raise RuntimeError("Gemini quota exhausted — Format 3 skipped.")

                log("🔍 Step 1/7: Researching moral dilemma...", fmt)
                research_list = research_dilemma()
                if manual:
                    from telegram.approver import wait_for_topic_approval
                    research = wait_for_topic_approval(research_list)
                else:
                    research = research_list[0] if isinstance(research_list, list) else research_list
                    
                log(f"   Dilemma: {research.get('dilemma_seed', '')[:60]}...", fmt)
                log(f"   {quota_tracker.status()}", fmt)

                log("📝 Step 2/7: Generating script...", fmt)
                script_data = generate_dilemma(research=research)
                script_data["dilemma_seed"] = research.get("dilemma_seed", "Moral dilemma topic")
                log(f"   Title: {script_data['title']}", fmt)
                log(f"   Closing Q: {script_data.get('closing_question', '')}", fmt)
                log(f"   {quota_tracker.status()}", fmt)

            with open(script_path, "w") as f:
                json.dump(script_data, f)

        # Step 3 — Voiceover
        if os.path.exists(voice_path):
            log("🎙️  Step 3/7: Loading cached voiceover...", fmt)
            audio_path     = voice_path
            audio_duration = _load_audio_duration(audio_path)
        else:
            log("🎙️  Step 3/7: Generating voiceover via Kokoro...", fmt)
            audio_path, audio_duration = generate_voiceover(
                script_data["script"], output_filename="voiceover_f3.mp3"
            )
        log(f"   Duration: {audio_duration:.1f}s", fmt)

        # Step 4 — Footage
        log("🎬 Step 4/7: Selecting gameplay footage...", fmt)
        footage_paths = fetch_footage(duration_needed=audio_duration + 2, fmt=3)
        log(f"   Clips: {len(footage_paths)}", fmt)

        # Step 5 — Captions
        if os.path.exists(caption_path):
            log("📄 Step 5/7: Loading cached captions...", fmt)
            with open(caption_path) as f:
                captions = json.load(f)
        else:
            log("📄 Step 5/7: Transcribing captions...", fmt)
            captions = transcribe_audio(audio_path, words_per_caption=3)
            with open(caption_path, "w") as f:
                json.dump(captions, f)
        log(f"   Chunks: {len(captions)}", fmt)

        # Step 6 — Render with closing question overlay
        log("🎞️  Step 6/7: Assembling video with closing question overlay...", fmt)
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        closing_q  = script_data.get("closing_question")
        video_path = build_video(
            footage_paths, audio_path, captions, audio_duration,
            f"short_f3_{ts}.mp4",
            closing_question=closing_q,
            fmt=3, script_data=script_data
        )
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            log("📤 Step 7/7: Uploading to YouTube...", fmt)
            result = upload_short(
                video_path, script_data["title"],
                script_data["description"], script_data["hashtags"],
            )
            log(f"   ✅ Live: {result['url']}", fmt)
            
            from analytics.tracker import log_upload
            from memory.content_log import add_used_topic
            if "video_id" in result:
                log_upload(result["video_id"], 3, script_data["dilemma_seed"], script_data.get("closing_question", ""))
            add_used_topic(script_data["dilemma_seed"], 3)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        log("🎉 Format 3 completed successfully!", fmt)
        return {"format": 3, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        log(f"❌ Format 3 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


# ── All Formats ───────────────────────────────────────────────────────────────

def run_all_formats(upload: bool = True, niche: str = None, manual: bool = False, resume: bool = False, fmt_list=["1", "2", "3"]):
    """
    Run all three formats in quota-priority order (F1 → F2 → F3).
    Skips remaining formats if Gemini quota runs out.
    """
    log("━" * 50)
    log(f"▶▶ Running all three formats | {quota_tracker.status()}")

    runners = []
    if "all" in fmt_list or "1" in fmt_list:
        runners.append(("1", lambda attempt=1: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume)))
    if "all" in fmt_list or "2" in fmt_list:
        runners.append(("2", lambda attempt=1: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume)))
    if "all" in fmt_list or "3" in fmt_list:
        runners.append(("3", lambda attempt=1: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume)))
    
    results = {}

    for fmt_name, runner in runners:
        if not quota_tracker.can_proceed(2):
            skipped = [f for f, _ in runners if f >= fmt_name]
            msg = f"Quota exhausted. Skipping Format(s): {', '.join(skipped)}"
            log(f"⚠️  {msg}")
            with open("./logs/pipeline.log", "a") as f:
                f.write(f"[QUOTA SKIP] {msg}\n")
            break

        for attempt in range(1, 4):
            try:
                results[fmt_name] = runner(attempt=attempt)
                break
            except Exception as e:
                if attempt < 3:
                    log(f"⚠️  Format {fmt_name} attempt {attempt} failed — retrying in 30s: {e}")
                    time.sleep(30)
                else:
                    log(f"❌ Format {fmt_name} failed after 3 attempts: {e}")

    log(f"✅ All-format run complete. {quota_tracker.status()}")
    return results


# ── Scheduler ─────────────────────────────────────────────────────────────────

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=lambda: run_format1(upload=True),
        trigger="cron", hour=FORMAT1_SCHEDULE_HOUR, minute=0,
        id="format1_daily", name="Format 1 — Facts",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        func=lambda: run_format2(upload=True),
        trigger="cron", hour=FORMAT2_SCHEDULE_HOUR, minute=0,
        id="format2_daily", name="Format 2 — Thriller",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        func=lambda: run_format3(upload=True),
        trigger="cron", hour=FORMAT3_SCHEDULE_HOUR, minute=0,
        id="format3_daily", name="Format 3 — Dilemma",
        misfire_grace_time=3600,
    )
    
    from analytics.tracker import check_performance
    from memory.content_log import purge_old_entries
    
    scheduler.add_job(
        func=check_performance,
        trigger="cron", hour=10, minute=0,
        id="analytics_daily", name="Daily Analytics Check"
    )
    
    scheduler.add_job(
        func=purge_old_entries,
        trigger="cron", hour=1, minute=0,
        id="purge_topics", name="Purge old topics"
    )

    log(
        f"⏰ Scheduler active — "
        f"F1@{FORMAT1_SCHEDULE_HOUR:02d}:00 UTC  "
        f"F2@{FORMAT2_SCHEDULE_HOUR:02d}:00 UTC  "
        f"F3@{FORMAT3_SCHEDULE_HOUR:02d}:00 UTC"
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler stopped.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Bot — 3 Formats")
    parser.add_argument(
        "mode",
        choices=["run", "dry-run", "schedule", "test-script", "test-voice"],
        default="run", nargs="?",
    )
    parser.add_argument("--niche", type=str, help="Override NICHE from .env (Format 1 only)")
    parser.add_argument(
        "--format", type=str, default="all",
        choices=["1", "2", "3", "all"],
        help="Which format(s) to run (default: all)",
    )
    parser.add_argument("--count", type=int, default=1, help="Times to run the pipeline")
    parser.add_argument("--reset-story", action="store_true", help="Reset Format 2 story arc and start fresh")
    parser.add_argument("--manual", action="store_true", help="Enable manual approval via Telegram")
    parser.add_argument("--resume", action="store_true", help="Resume from cached files without clearing temp directory")
    return parser.parse_args()


if __name__ == "__main__":
    args   = parse_args()
    upload = args.mode not in ("dry-run", "test-script", "test-voice")

    if args.reset_story:
        reset_state()

    if args.mode == "test-script":
        fmt = args.format if args.format != "all" else "1"
        print(f"\n{'═' * 60}")
        print(f"FORMAT {fmt} — TEST SCRIPT (no upload, no video)")
        print("═" * 60)
        if fmt == "1":
            research = research_topic(niche=args.niche)
            data = generate_script(niche=args.niche, research=research)
        elif fmt == "2":
            state    = load_state()
            research = research_thriller() if state.get("part_number", 0) == 0 else None
            data     = generate_thriller(story_state=state, research=research)
        else:
            research = research_dilemma()
            data     = generate_dilemma(research=research)
        print(f"TITLE:    {data['title']}")
        print(f"SCRIPT:\n{data['script']}")
        if data.get("closing_question"):
            print(f"\nCLOSING Q: {data['closing_question']}")
        if data.get("cliffhanger"):
            print(f"\nCLIFFHANGER: {data['cliffhanger']}")

    elif args.mode == "test-voice":
        fmt = args.format if args.format != "all" else "1"
        if fmt == "1":
            research = research_topic(niche=args.niche)
            data = generate_script(niche=args.niche, research=research)
        elif fmt == "2":
            state    = load_state()
            research = research_thriller() if state.get("part_number", 0) == 0 else None
            data     = generate_thriller(story_state=state, research=research)
        else:
            research = research_dilemma()
            data     = generate_dilemma(research=research)
        path, dur = generate_voiceover(data["script"])
        print(f"\n✅ Voice file: {path} ({dur:.1f}s)")

    elif args.mode == "schedule":
        run_scheduler()

    elif args.mode in ("run", "dry-run"):
        for i in range(args.count):
            if args.count > 1:
                log(f"\n{'='*60}\n▶ Pipeline Run {i+1}/{args.count}\n{'='*60}")
            
            fmt_list = ["1", "2", "3"] if args.format == "all" else [args.format]
            run_all_formats(upload, niche=args.niche, manual=args.manual, resume=args.resume, fmt_list=fmt_list)
