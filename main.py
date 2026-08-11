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
import sys
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
from video.notebooklm_footage import fetch_notebooklm_footage
from video.captions import transcribe_audio
from video.editor import build_video
from uploader.youtube import upload_video
from uploader.instagram import upload_reel
import quota_tracker
def handle_ig_upload(script_data: dict, video_path: str, schedule_time, fmt: str) -> str:
    from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
    if not (IG_ACCESS_TOKEN and IG_ACCOUNT_ID):
        return None
        
    log("📸 Processing Instagram Reels...", fmt)
    caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
    
    if schedule_time:
        from uploader.instagram import get_public_url
        public_url = get_public_url(video_path)
        
        pending_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "pending_ig.json")
        pending = []
        if os.path.exists(pending_file):
            with open(pending_file, "r") as pf:
                try: pending = json.load(pf)
                except: pass
                
        pending.append({
            "url": public_url,
            "caption": caption,
            "schedule_time": schedule_time.isoformat(),
            "fmt": fmt
        })
        with open(pending_file, "w") as pf:
            json.dump(pending, pf)
            
        log(f"   ✅ Saved to pending_ig.json for {schedule_time.isoformat()} via {public_url}", fmt)
        return f"scheduled_{int(time.time())}"
    else:
        from uploader.instagram import upload_reel
        return upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str, fmt: str = ""):
    ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[FORMAT {fmt}] " if fmt else ""
    line   = f"[{ts}] {prefix}{msg}"
    print(line, flush=True)
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

    # Also wipe the cached script and NotebookLM state in the memory folder to force a new topic
    mem_dir = os.path.join(os.path.dirname(TEMP_DIR), "memory")
    script_path = os.path.join(mem_dir, f"script_f{fmt_num}.json")
    state_path = os.path.join(mem_dir, f"nblm_state_f{fmt_num}.json")
    for file_path in [script_path, state_path]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
                
    # Wipe any cached notebooklm videos for this format
    import glob
    for vid in glob.glob(os.path.join(mem_dir, f"notebooklm_f{fmt_num}_*.mp4")):
        try:
            os.remove(vid)
        except Exception:
            pass


def _load_audio_duration(path: str) -> float:
    try:
        return len(pydub.AudioSegment.from_mp3(path)) / 1000.0
    except Exception:
        return 0.0


# ── FORMAT 1: Mind-Blowing Facts ─────────────────────────────────────────────

def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "1") -> dict:
    fmt = fmt_id
    base_fmt = str(fmt).split("_")[0]
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 1, "skipped": True}

    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(fmt):
            log("⏭️  Format 1 already uploaded today. Skipping.", fmt)
            return {"format": 1, "skipped": True}

    log(f"🚀 Starting | niche: {niche or NICHE} | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(fmt)

    script_path  = os.path.join(os.path.dirname(TEMP_DIR), "memory", "script_f1.json")
    caption_path = os.path.join(TEMP_DIR, "captions_f1.json")
    voice_path   = os.path.join(TEMP_DIR, "voiceover_f1.mp3")

    try:
        # If resume_only and nblm state exists, load script from nblm state and jump straight to Step 4
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            # Steps 1 & 2 — Research + Script
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("chosen_topic", ""), 1):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(fmt)
                else:
                    log("📝 Steps 1 & 2: Loading cached script...", fmt)
                    script_data = cached_data
                    research = {"chosen_topic": script_data.get("chosen_topic", "Cached")}
                    
            if not script_data:
                if mock:
                    log("🧪 Dry run: Using static mock script for Format 1...", fmt)
                    script_data = {
                        "title": "The Triple Point of Water",
                        "description": "How water can boil and freeze at the exact same time.",
                        "hashtags": ["#shorts", "#science", "#physics"],
                        "script": "In everyday life, water exists in three distinct states: solid ice, liquid water, or gaseous steam. We assume these states are strictly divided by temperature: ice melts at zero degrees Celsius, and water boils at one hundred degrees Celsius. However, in the world of thermodynamics, these boundaries can completely break down under the right conditions. This phenomenon is known as the 'triple point' of water. The triple point occurs at a very specific temperature—exactly 0.01 degrees Celsius—and an extremely low atmospheric pressure of 611.65 pascals, which is about 0.6% of the normal air pressure at sea level. When water is placed in a vacuum chamber and stabilized at these precise parameters, the liquid water, solid ice, and gaseous vapor coexist in stable thermodynamic equilibrium. Visually, this creates a bizarre and mind-bending spectacle: the water vigorously boils, releasing large bubbles of steam, while simultaneously forming delicate crystals of solid ice right on the surface. This happens because the low pressure lowers the boiling point of the water to its freezing point, causing rapid evaporation that cools the remaining liquid into ice. It is a stunning demonstration that temperature is only half of the story—pressure dictates reality.",
                        "hook": "Boil and freeze at the same time",
                        "pexels_keyword": "Boiling ice water vacuum chamber thermodynamics",
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
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("chosen_topic", script_data.get("title", "")), int(base_fmt))

        # Step 4 — Footage (Direct video delivery)
        log("🎬 Step 4/7: Generating NotebookLM video (voiceover & subtitles built-in)...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=45.0,
            fmt=1,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            yt_tracker = os.path.join(TEMP_DIR, f"yt_tracker_f{fmt}.json")
            if os.path.exists(yt_tracker):
                with open(yt_tracker, "r") as f:
                    result = json.load(f)
                log(f"⏭️ YouTube already uploaded: {result.get('url')}", fmt)
            else:
                log("📤 Step 7/7: Uploading to YouTube...", fmt)
                thumb_path = video_path.replace(".mp4", "_thumb.jpg")
                result = upload_video(
                    video_path, script_data["title"],
                    script_data["description"], script_data["hashtags"],
                    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
                    is_short=True, schedule_time=schedule_time
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 1, script_data.get("chosen_topic", ""), script_data.get("hook_angle", ""))
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                ig_post_id = handle_ig_upload(script_data, video_path, schedule_time, fmt)
                if ig_post_id: result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(fmt)
        
        log("🎉 Format 1 completed successfully!", fmt)
        return {"format": 1, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 1, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 1 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


# ── FORMAT 2: Serialized Thriller ─────────────────────────────────────────────

def run_format2(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "2") -> dict:
    from generator.script import generate_thriller
    from generator.researcher import research_thriller
    
    fmt = "2"
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 2, "skipped": True}

    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(fmt):
            log("⏭️  Format 2 already uploaded today. Skipping.", fmt)
            return {"format": 2, "skipped": True}

    log(f"🚀 Starting The Butterfly Effect | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(fmt)

    script_path  = os.path.join(os.path.dirname(TEMP_DIR), "memory", "script_f2.json")
    caption_path = os.path.join(TEMP_DIR, "captions_f2.json")
    voice_path   = os.path.join(TEMP_DIR, "voiceover_f2.mp3")

    try:
        # If resume_only and nblm state exists, load script from nblm state and jump straight to Step 4
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            # Steps 1 & 2 — Research + Script
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("used_topic_seed", cached_data.get("title", "")), 2):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(fmt)
                else:
                    log("📝 Steps 1 & 2: Loading cached script...", fmt)
                    script_data = cached_data

            if not script_data:
                if mock:
                    log("🧪 Dry run: Using static mock script for Format 2...", fmt)
                    script_data = {
                        "title": "The Antique Mirror",
                        "description": "Liam bought an antique mirror, but his reflection was lagging...",
                        "hashtags": ["#shorts", "#thriller", "#mystery"],
                        "script": "Liam was a collector of oddities, always searching the dust-caked shelves of antique stores for items with a past. Yesterday, he found a massive, heavy brass-framed mirror in the cellar of a shop on Elm Street. The shopkeeper practically threw it at him for twenty dollars, refusing to explain its origin. Liam hung it in his bedroom, admiring the way the glass caught the late afternoon sun. But as night fell, he noticed something unsettling. While sitting at his desk, he caught his reflection moving out of the corner of his eye. When he turned to face it, the mirror image was perfectly still. Intrigued, Liam stood up and raised his right hand. The reflection stood still for a solid second, before slowly, stiffly lifting its own hand to match. Liam froze, cold dread pooling in his stomach. He raised his hand again. One. Two. The reflection lagged behind. Terrified, he walked closer to the glass, his face inches from the cold surface. He stared into his own mirrored eyes. Slowly, the reflection's lips parted into a wide, unnatural grin that Liam was definitely not making. The mirror image leaned forward, pressed its hands against the glass, and whispered in a dry, rasping voice: get out.",
                        "hook": "The Antique Mirror",
                        "pexels_keyword": "Moody antique mirror, lagging reflection, slow camera zoom"
                    }
                else:
                    if not quota_tracker.can_proceed(2):
                        raise RuntimeError("Gemini quota exhausted — Format 2 skipped.")
                    log("🔍 Step 1/7: Researching thriller story concept...", fmt)
                    research = research_thriller()
                    log(f"   Premise: {research.get('premise')[:60]}...", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                    log("📝 Step 2/7: Generating single-episode script...", fmt)
                    script_data = generate_thriller(research=research)
                    log(f"   Title: {script_data['title']}", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("title", ""), int(fmt))

        # Step 4 — Footage (Direct video delivery)
        log("🎬 Step 4/7: Generating NotebookLM video (voiceover & subtitles built-in)...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=45.0,
            fmt=2,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            yt_tracker = os.path.join(TEMP_DIR, f"yt_tracker_f{fmt}.json")
            if os.path.exists(yt_tracker):
                with open(yt_tracker, "r") as f:
                    result = json.load(f)
                log(f"⏭️ YouTube already uploaded: {result.get('url')}", fmt)
            else:
                log("📤 Step 7/7: Uploading to YouTube...", fmt)
                thumb_path = video_path.replace(".mp4", "_thumb.jpg")
                result = upload_video(
                    video_path, script_data["title"],
                    script_data["description"], script_data["hashtags"],
                    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
                    is_short=True, schedule_time=schedule_time
                )
                log(f"   ✅ Live: {result['url']}", fmt)
                
                # Post-upload tracking
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 2, script_data["title"], script_data["hook"])
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                ig_post_id = handle_ig_upload(script_data, video_path, schedule_time, fmt)
                if ig_post_id: result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
                
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(fmt)

        log("🎉 Format 2 completed successfully!", fmt)
        return {"format": 2, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 2, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 2 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise



# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

def run_format3(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "3") -> dict:
    fmt = fmt_id
    base_fmt = str(fmt).split("_")[0]
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 3, "skipped": True}

    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(fmt):
            log("⏭️  Format 3 already uploaded today. Skipping.", fmt)
            return {"format": 3, "skipped": True}

    log(f"🚀 Starting Everyday Brain Glitches | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(fmt)

    script_path  = os.path.join(os.path.dirname(TEMP_DIR), "memory", "script_f3.json")
    caption_path = os.path.join(TEMP_DIR, "captions_f3.json")
    voice_path   = os.path.join(TEMP_DIR, "voiceover_f3.mp3")

    try:
        # If resume_only and nblm state exists, load script from nblm state and jump straight to Step 4
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            # Steps 1 & 2 — Research + Script
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("dilemma_seed", ""), 3):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(fmt)
                else:
                    log("📝 Steps 1 & 2: Loading cached dilemma script...", fmt)
                    script_data = cached_data

            if not script_data:
                if mock:
                    log("🧪 Dry run: Using static mock script for Format 3...", fmt)
                    script_data = {
                        "title": "The Million Dollar Button",
                        "description": "A dark dilemma: wealth versus a stranger's memories.",
                        "hashtags": ["#shorts", "#dilemma", "#philosophy"],
                        "script": "Imagine walking into a room to find a sleek, black box sitting on a mahogany table. In the center of the box is a single, glowing red button. A representative from a mysterious organization presents you with a simple, binding contract: if you press the button, you will instantly receive one million dollars, tax-free. However, there is a catch. The moment the button clicks down, a random person somewhere in the world will lose all of their memories forever. They won't die, but their entire history, their name, their childhood, and their love for their family will be instantly wiped clean, leaving them a complete blank slate. If you choose not to press the button, you walk away with nothing, and the stranger's life remains untouched. This dilemma pits extreme self-preservation and life-altering wealth against absolute altruism and the moral duty to prevent harm. On one hand, one million dollars could secure your family's future, pay off your debts, and give you complete freedom. On the other hand, erasing a human being's memories is arguably a form of psychological murder, destroying the very essence of who they are for personal gain. You stand before the button, feeling the weight of the red light. The timer is ticking. What would you do?",
                        "hook": "The million dollar button",
                        "closing_question": "What would you do?",
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
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("dilemma_seed", script_data.get("title", "")), int(base_fmt))

        # Step 4 — Footage (Direct video delivery)
        log("🎬 Step 4/7: Generating NotebookLM video (voiceover & subtitles built-in)...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=45.0,
            fmt=3,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            yt_tracker = os.path.join(TEMP_DIR, f"yt_tracker_f{fmt}.json")
            if os.path.exists(yt_tracker):
                with open(yt_tracker, "r") as f:
                    result = json.load(f)
                log(f"⏭️ YouTube already uploaded: {result.get('url')}", fmt)
            else:
                log("📤 Step 7/7: Uploading to YouTube...", fmt)
                thumb_path = video_path.replace(".mp4", "_thumb.jpg")
                result = upload_video(
                    video_path, script_data["title"],
                    script_data["description"], script_data["hashtags"],
                    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
                    is_short=True, schedule_time=schedule_time
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 3, script_data["dilemma_seed"], script_data.get("closing_question", ""))
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                ig_post_id = handle_ig_upload(script_data, video_path, schedule_time, fmt)
                if ig_post_id: result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(fmt)

        log("🎉 Format 3 completed successfully!", fmt)
        return {"format": 3, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 3, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 3 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


# ── FORMAT 4: Dark Psychology & Insane Real-Life Cases ────────────────────────

def run_format4(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "4") -> dict:
    from generator.script import generate_psychology
    from generator.researcher import research_psychology
    
    fmt = "4"
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 4, "skipped": True}

    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(fmt):
            log("⏭️  Format 4 already uploaded today. Skipping.", fmt)
            return {"format": 4, "skipped": True}

    log(f"🚀 Starting Genius Loopholes Case study | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(fmt)

    script_path  = os.path.join(os.path.dirname(TEMP_DIR), "memory", "script_f4.json")

    try:
        # If resume_only and nblm state exists, load script from nblm state and jump straight to Step 4
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            # Steps 1 & 2 — Research + Script
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("used_topic_seed", cached_data.get("title", "")), 4):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(fmt)
                else:
                    log("📝 Steps 1 & 2: Loading cached script...", fmt)
                    script_data = cached_data

            if not script_data:
                if mock:
                    log("🧪 Dry run: Using static mock script for Format 4...", fmt)
                    script_data = {
                        "title": "The Imposter Frédéric Bourdin",
                        "description": "How a con artist convinced a family he was their missing son...",
                        "hashtags": ["#shorts", "#psychology", "#manipulation", "#truecrime"],
                        "script": "In 1997, a quiet suburban family in San Antonio, Texas, received a phone call they had prayed for. Their sixteen-year-old son, Nicholas Barclay, who had vanished three years prior, had been found alive in a youth shelter in Spain. The family flew to Europe immediately, desperate to bring their boy home. When they arrived, the boy they met had blue eyes, a French accent, and looked years older than Nicholas. Yet, in their desperate grief, they embraced him and brought him back to Texas. For nearly four months, they lived with a stranger. In reality, this was Frédéric Bourdin, a twenty-three-year-old French con artist known as 'The Chameleon,' who had spent his life assuming the identities of missing children. Bourdin dyed his hair, spoke with a forced American drawl, and wore a cap to hide his receding hairline. How did he pull off such a massive manipulation? Dark psychology experts suggest that Bourdin exploited the family's 'motivated blindness'—their overwhelming desire to believe their tragedy was over was so powerful that their brains actively filtered out the obvious differences in his appearance, accent, and mannerisms. It was only when a private investigator noticed the different eye colors that the illusion shattered, raising the chilling question: did the family truly believe he was Nicholas, or did they just need to believe it?",
                        "hook": "The Imposter",
                        "pexels_keyword": "Suburban house shadow, vintage photo frame, mysterious figure, slow zoom"
                    }
                else:
                    if not quota_tracker.can_proceed(2):
                        raise RuntimeError("Gemini quota exhausted — Format 4 skipped.")
                    log("🔍 Step 1/7: Researching dark psychology case...", fmt)
                    research = research_psychology()
                    log(f"   Premise: {research.get('premise')[:60]}...", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                    log("📝 Step 2/7: Generating case study script...", fmt)
                    script_data = generate_psychology(research=research)
                    log(f"   Title: {script_data['title']}", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data.get("title", "")), int(base_fmt))

        # Step 4 — Footage (Direct video delivery)
        log("🎬 Step 4/7: Generating NotebookLM video (voiceover & subtitles built-in)...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=45.0,
            fmt=4,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        # Step 7 — Upload
        if upload:
            yt_tracker = os.path.join(TEMP_DIR, f"yt_tracker_f{fmt}.json")
            if os.path.exists(yt_tracker):
                with open(yt_tracker, "r") as f:
                    result = json.load(f)
                log(f"⏭️ YouTube already uploaded: {result.get('url')}", fmt)
            else:
                log("📤 Step 7/7: Uploading to YouTube...", fmt)
                thumb_path = video_path.replace(".mp4", "_thumb.jpg")
                result = upload_video(
                    video_path, script_data["title"],
                    script_data["description"], script_data["hashtags"],
                    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
                    is_short=True, schedule_time=schedule_time
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                # Post-upload tracking
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 4, script_data["title"], script_data.get("hook", ""))
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                ig_post_id = handle_ig_upload(script_data, video_path, schedule_time, fmt)
                if ig_post_id: result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
                
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(fmt)

        log("🎉 Format 4 completed successfully!", fmt)
        return {"format": 4, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 4, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 4 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise


def run_format5(upload: bool = True, attempt: int = 1, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "5"):
    """
    Format 5: Long-Form Cinematic Widescreen Video.
    Generated on a 2-day schedule.
    """
    from generator.script import generate_long_video
    from video.notebooklm_footage import fetch_notebooklm_footage
    from uploader.youtube import upload_video
    fmt = 5
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    result = {}

    if attempt > 1:
        log(f"⚠️  Retrying Format 5 (Attempt {attempt}/3)...", fmt)
        time.sleep(10)
    else:
        log(f"━━━━━━━━━━━━━━━━━━ FORMAT 5: LONG-FORM VIDEO ━━━━━━━━━━━━━━━━━━", fmt)

    if not quota_tracker.can_proceed(2) and not (resume_only and os.path.exists(state_path)):
        log("⏭️  Quota exhausted. Skipping Format 5.", fmt)
        return {"format": 5, "skipped": True}

    log(f"🚀 Starting Long-Form Video | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(fmt)

    script_path  = os.path.join(os.path.dirname(TEMP_DIR), "memory", "script_f5.json")

    try:
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("used_topic_seed", cached_data.get("title", "")), 5):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(fmt)
                else:
                    log("📝 Loading cached script...", fmt)
                    script_data = cached_data

            if not script_data:
                if mock:
                    log("🧪 Dry run: Mock script", fmt)
                    script_data = {
                        "topic": "Mock", "title": "Mock", "description": "Mock", "hashtags": ["#mock"], "script": "Mock", "notebooklm_instructions": "Mock"
                    }
                else:
                    if not quota_tracker.can_proceed(2):
                        raise RuntimeError("Gemini quota exhausted.")
                    log("📝 Step 1 & 2: Generating long-form script...", fmt)
                    script_data = generate_long_video()
                    log(f"   Title: {script_data['title']}", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data.get("title", "")), int(base_fmt))

        log("🎬 Step 4: Generating NotebookLM 16:9 video...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=180.0,
            fmt=5,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        if upload:
            log("📤 Step 7: Uploading to YouTube...", fmt)
            thumb_path = video_path.replace(".mp4", "_thumb.jpg")
            result = upload_video(
                video_path, script_data["title"],
                script_data["description"], script_data["hashtags"],
                thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
                is_short=False
            )
            log(f"   ✅ YouTube Live: {result['url']}", fmt)
            
            try:
                state_file = "memory/pipeline_state.json"
                if os.path.exists(state_file):
                    with open(state_file, "r") as pf:
                        ps = json.load(pf)
                    from datetime import datetime
                    ps["last_long_video_date"] = datetime.now().strftime("%Y-%m-%d")
                    with open(state_file, "w") as pf:
                        json.dump(ps, pf, indent=4)
            except Exception as e:
                log(f"⚠️ Could not save last_long_video_date: {e}", fmt)
            
            from analytics.tracker import log_upload
            from memory.content_log import add_used_topic
            if "video_id" in result:
                log_upload(result["video_id"], 5, script_data["title"], script_data.get("hook", ""))
            add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 5)
        else:
            log("⏭️  Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(fmt)

        log("🎉 Format 5 completed successfully!", fmt)
        return {"format": 5, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 5, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 5 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise

# ── All Formats ───────────────────────────────────────────────────────────────

def run_all_formats(upload: bool = True, niche: str = None, manual: bool = False, resume: bool = False, mock: bool = False, fmt_list=["1", "2", "3", "4"], resume_only: bool = False, schedule_times: dict = None):
    """
    Run all formats in quota-priority order (F1 → F2 → F3 → F4).
    Skips remaining formats if Gemini quota runs out.
    """
    log("━" * 50)
    log(f"▶▶ Running formats | {quota_tracker.status()}")
    
    schedule_times = schedule_times or {}

    runners = []
    
    # Expand "all" to the standard 4 formats
    expanded_fmt_list = ["1", "2", "3", "4"] if "all" in fmt_list else fmt_list
    
    for fmt_name in expanded_fmt_list:
        base_fmt = fmt_name.split("_")[0]
        st = schedule_times.get(fmt_name)
        
        if base_fmt == "1":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "2":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "3":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "4":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))

    # ── 2-Day Scheduling Logic for Format 5 ──
    try:
        state_file = "memory/pipeline_state.json"
        should_run_f5 = False
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                ps = json.load(f)
            last_date_str = ps.get("last_long_video_date")
            if last_date_str:
                from datetime import datetime
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                if (datetime.now().date() - last_date).days >= 2:
                    should_run_f5 = True
            else:
                should_run_f5 = True
        else:
            should_run_f5 = True

        if ("all" in fmt_list or "5" in fmt_list) and should_run_f5:
            runners.append(("5", lambda attempt=1: run_format5(upload=upload, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only)))
    except Exception as e:
        log(f"⚠️ Could not evaluate Format 5 scheduling: {e}")

    results = {}
    pipeline_has_errors = False

    for fmt_name, runner in runners:
        if not quota_tracker.can_proceed(2):
            skipped = [f for f, _ in runners if f >= fmt_name]
            msg = f"Quota exhausted. Skipping Format(s): {', '.join(skipped)}"
            log(f"⚠️  {msg}")
            try:
                from telegram.approver import send_telegram_notification
                send_telegram_notification(f"⚠️ <b>Pipeline Quota Skip</b>\n{msg}")
            except: pass
            with open("./logs/pipeline.log", "a") as f:
                f.write(f"[QUOTA SKIP] {msg}\n")
            break

        for attempt in range(1, 4):
            try:
                results[fmt_name] = runner(attempt=attempt)
                
                res = results[fmt_name]
                if res.get("skipped"):
                    break
                if res.get("rendering"):
                    title = res.get('script', {}).get('title', 'Unknown')
                    if not resume_only:
                        try:
                            from telegram.approver import notify_pipeline_running
                            notify_pipeline_running(fmt_name, title)
                        except: pass
                    break

                if "result" in res and res.get("result", {}).get("url"):
                    # Success
                    title = res.get('script', {}).get('title', 'Unknown')
                    yt_url = res["result"].get("url")
                    ig_post_id = res["result"].get("ig_post_id")
                    try:
                        from telegram.approver import notify_pipeline_success
                        notify_pipeline_success(fmt_name, title, yt_url, ig_post_id)
                    except: pass

                # Clean cache code remains the same
                video_path = res.get("video_path")
                result_data = res.get("result", {})
                from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
                ig_configured = bool(IG_ACCESS_TOKEN and IG_ACCOUNT_ID)
                ig_success = bool(result_data.get("ig_post_id")) if isinstance(result_data, dict) else False

                if video_path and os.path.exists(video_path):
                    if not ig_configured or ig_success:
                        try:
                            os.remove(video_path)
                            log(f"🧹 Cleaned up uploaded video cache: {os.path.basename(video_path)}")
                        except Exception as de:
                            log(f"⚠️ Could not delete uploaded video cache: {de}")
                    else:
                        log(f"ℹ️ Preserving video file in memory/ folder for manual re-upload: {os.path.basename(video_path)}")

                break
            except Exception as e:
                import traceback
                err_msg = str(e)
                tb = traceback.format_exc()
                
                if attempt < 3:
                    log(f"⚠️  Format {fmt_name} attempt {attempt} failed — retrying in 30s: {e}")
                    warn_msg = f"<b>⚠️ Format {fmt_name} Attempt {attempt} Failed</b>\nError: <code>{err_msg}</code>\nRetrying in 30s..."
                    try:
                        from telegram.approver import send_telegram_notification
                        send_telegram_notification(warn_msg)
                    except: pass
                    time.sleep(30)
                else:
                    is_timeout = any(kw in err_msg.lower() for kw in ["timeout", "timed out", "in progress", "rendering in background"])
                    if is_timeout:
                        log(f"⏳ Format {fmt_name} is still rendering in the background after 3 attempts. Will check again later.")
                    else:
                        log(f"❌ Format {fmt_name} failed completely after 3 attempts: {e}")
                        pipeline_has_errors = True
                        try:
                            from telegram.approver import notify_pipeline_failed
                            notify_pipeline_failed(err_msg, "Check logs for traceback")
                        except: pass
                    
                    # Do not raise e; just break the retry loop to continue to the next format!
                    break

    log(f"✅ All-format run complete. {quota_tracker.status()}")
    
    # 💾 Save Memory State to GitHub to prevent Render Amnesia!
    try:
        from memory.saver import push_memory_to_github
        push_memory_to_github()
    except Exception as e:
        log(f"⚠️ Failed to push memory to GitHub: {e}")
        
    if pipeline_has_errors:
        raise RuntimeError("One or more formats failed completely.")
    return results


# ── Scheduler ─────────────────────────────────────────────────────────────────

def get_schedule_mapping(num_reels):
    """
    Returns a list of (format_id, target_hour) based on daily requested reels (1-6).
    Uses a round-robin approach for formats: 1 -> 2 -> 3 -> 4 -> 1...
    Hours are spaced out as much as possible across a 24-hour period.
    """
    if num_reels == 1:
        hours = [15]
    elif num_reels == 2:
        hours = [8, 20] # 12 hours apart
    elif num_reels == 3:
        hours = [7, 15, 23] # 8 hours apart
    elif num_reels == 4:
        hours = [6, 12, 18, 23] # ~6 hours apart
    elif num_reels == 5:
        hours = [5, 10, 15, 19, 23] # ~4.5 hours apart
    elif num_reels >= 6:
        hours = [4, 8, 12, 16, 20, 23] # ~4 hours apart
        num_reels = 6 # Cap at 6 for now
    else:
        # Default to N=4 (Current Behavior)
        hours = [9, 13, 17, 21]
        num_reels = 4

    mapping = []
    base_formats = ["1", "2", "3", "4"]
    format_counts = {"1": 0, "2": 0, "3": 0, "4": 0}

    for i in range(num_reels):
        base_fmt = base_formats[i % len(base_formats)]
        format_counts[base_fmt] += 1
        
        # Suffix with _N if repeated to ensure unique ID in run_all_formats
        fmt_id = base_fmt if format_counts[base_fmt] == 1 else f"{base_fmt}_{format_counts[base_fmt]}"
        mapping.append((fmt_id, hours[i]))
        
    return mapping

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

    # Run the powerful Time-Window Dispatcher every 15 minutes
    # It will automatically detect if it's time for a new format, or if it needs to retry a failed one!
    def tick_dispatcher():
        import subprocess
        print("⏰ Scheduler Tick: Triggering Dispatcher Check...")
        subprocess.run(["python", "main.py", "run", "--resume-check"])

    scheduler.add_job(
        func=tick_dispatcher,
        trigger="cron", minute="*/15",
        id="dispatcher_tick", name="15-Minute Dispatcher Tick",
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

    log("⏰ Scheduler active — Dispatcher ticking every 15 minutes to manage time windows.")
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
        choices=["1", "2", "3", "4", "all"],
        help="Which format(s) to run (default: all)",
    )
    parser.add_argument("--count", type=int, default=1, help="Times to run the pipeline")
    parser.add_argument("--reset-story", action="store_true", help="Reset Format 2 story arc and start fresh")
    parser.add_argument("--manual", action="store_true", help="Enable manual approval via Telegram")
    parser.add_argument("--resume", action="store_true", help="Resume from cached files without clearing temp directory")
    parser.add_argument("--resume-only", action="store_true", help="Backward compatibility flag")
    parser.add_argument("--fresh", action="store_true", help="Start a daily fresh run enforcing state logic")
    parser.add_argument("--resume-check", action="store_true", help="Resume pending render enforcing state logic")
    parser.add_argument("--mock", action="store_true", help="Use static mock scripts instead of live research during dry-run")
    parser.add_argument("--batch", action="store_true", help="Generate all formats at once and schedule them on YouTube using publishAt")
    parser.add_argument("--ig-scheduler", action="store_true", help="Run the Instagram scheduler to post pending reels")
    parser.add_argument("--daily-reels", type=int, default=None, help="Number of reels to post today (1-6) (overrides config)")
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
            research = research_thriller()
            data     = generate_thriller(research=research)
        elif fmt == "3":
            research = research_dilemma()
            data     = generate_dilemma(research=research)
        else:
            research = research_psychology()
            data     = generate_psychology(research=research)
        print(f"TITLE:    {data['title']}")
        print(f"SCRIPT:\n{data['script']}")
        if data.get("closing_question"):
            print(f"\nCLOSING Q: {data['closing_question']}")

    elif args.mode == "test-voice":
        fmt = args.format if args.format != "all" else "1"
        if fmt == "1":
            research = research_topic(niche=args.niche)
            data = generate_script(niche=args.niche, research=research)
        elif fmt == "2":
            research = research_thriller()
            data     = generate_thriller(research=research)
        elif fmt == "3":
            research = research_dilemma()
            data     = generate_dilemma(research=research)
        else:
            research = research_psychology()
            data     = generate_psychology(research=research)
        path, dur = generate_voiceover(data["script"])
        print(f"\n✅ Voice file: {path} ({dur:.1f}s)")

    elif args.mode == "schedule":
        run_scheduler()

    elif args.mode in ("run", "dry-run"):
        if args.batch:
            from datetime import datetime, timezone, timedelta
            from config import DAILY_REELS
            
            # Use CLI arg if provided, otherwise config, capped at 6
            reels_count = args.daily_reels if args.daily_reels is not None else DAILY_REELS
            reels_count = max(1, min(6, reels_count))
            
            # Set the base schedule times for the current day in UTC
            now = datetime.now(timezone.utc)
            base_date = now.replace(minute=0, second=0, microsecond=0)
            
            # --- ADAPTIVE SCHEDULING LOGIC ---
            import json, os
            last_pending_time = None
            memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
            pending_ig_path = os.path.join(memory_dir, "pending_ig.json")
            if os.path.exists(pending_ig_path):
                try:
                    with open(pending_ig_path, "r") as f:
                        pending_data = json.load(f)
                        for item in pending_data:
                            if "schedule_time" in item:
                                dt = datetime.fromisoformat(item["schedule_time"])
                                if last_pending_time is None or dt > last_pending_time:
                                    last_pending_time = dt
                except Exception:
                    pass
            
            last_assigned_time = last_pending_time
            min_gap_hours = max(2, min(4, 24 // (reels_count + 1)))
            # ----------------------------------
            
            schedule_mapping = get_schedule_mapping(reels_count)
            schedule_times = {}
            fmt_list = []
            
            for fmt_id, hour in schedule_mapping:
                target_time = base_date.replace(hour=hour)
                
                # Adaptive logic: if target time passed, bring it up to now + 15 mins
                if target_time < now:
                    target_time = now + timedelta(minutes=15)
                
                # Prevent clumping: must be at least min_gap_hours after previously assigned post
                if last_assigned_time is not None:
                    min_acceptable_time = last_assigned_time + timedelta(hours=min_gap_hours)
                    if target_time < min_acceptable_time:
                        target_time = min_acceptable_time
                
                last_assigned_time = target_time
                schedule_times[fmt_id] = target_time
                fmt_list.append(fmt_id)
                
            log(f"🚀 Starting BATCH MODE. Generating and scheduling {len(schedule_times)} formats.")
            for fmt_id, stime in schedule_times.items():
                log(f"   Format {fmt_id.split('_')[0]} -> Scheduled for {stime.isoformat()}")
            
            try:
                import os
                from memory.state_manager import has_active_nblm_state, get_state, set_active_render, start_fresh_run, mark_posted, mark_skipped, mark_failed
                
                memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
                
                # If specific format requested, override the batch cycle
                if args.format != "all":
                    fmt_list = [args.format]
                
                # --- NEW: Smart Resume Check ---
                # If batch is triggered but there are already active renders, automatically switch to RESUME MODE
                state = get_state()
                has_active = has_active_nblm_state(memory_dir)
                
                if not has_active and state.get("status") == "posted":
                    log("⏭️ Pipeline is already 'posted' for today. Skipping new batch generation.")
                    results = {}
                elif has_active:
                    log("⏳ Active NotebookLM render state files detected during Batch Run. Automatically switching to RESUME MODE...")
                    if state.get("status") != "running":
                        start_fresh_run()
                    set_active_render(True)
                    
                    results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=True, mock=args.mock, fmt_list=fmt_list, resume_only=True, schedule_times=schedule_times)
                else:
                    if state.get("status") != "running":
                        start_fresh_run()
                    results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=args.resume, mock=args.mock, fmt_list=fmt_list, resume_only=args.resume_only, schedule_times=schedule_times)
                
                is_rendering = any(res.get("rendering") for res in results.values() if isinstance(res, dict))
                if is_rendering:
                    set_active_render(True)
                else:
                    posted_formats_this_run = [f_id for f_id, res in results.items() if isinstance(res, dict) and res.get("result", {}).get("url")]
                    if posted_formats_this_run:
                        for pf in posted_formats_this_run: mark_posted(pf)
                    elif not has_active and state.get("status") != "posted":
                        mark_skipped("Pipeline completed but no format was uploaded.")
            except Exception as e:
                import traceback
                from memory.state_manager import mark_failed
                try: mark_failed(str(e))
                except: pass
                log(f"❌ Batch run failed: {e}")
                log(traceback.format_exc())
                exit(1)
            exit(0)
            
        elif args.ig_scheduler:
            from datetime import datetime, timezone
            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            from uploader.instagram import publish_from_url
            
            log("⏰ Running IG Scheduler...")
            pending_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "pending_ig.json")
            if not os.path.exists(pending_file):
                log("   ⏭️ No pending_ig.json found.")
                exit(0)
                
            with open(pending_file, "r") as pf:
                pending = json.load(pf)
                
            now = datetime.now(timezone.utc)
            remaining = []
            uploaded_any = False
            
            for post in pending:
                target_time = datetime.fromisoformat(post["schedule_time"])
                if now >= target_time:
                    log(f"   🚀 Publishing scheduled IG post for Format {post.get('fmt')} (Scheduled: {target_time.isoformat()})")
                    try:
                        post_id = publish_from_url(post["url"], post["caption"], IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                        log(f"   ✅ Successfully posted! ID: {post_id}")
                        uploaded_any = True
                    except Exception as e:
                        log(f"   ❌ Failed to publish IG post: {e}")
                        remaining.append(post) # Keep in queue if failed
                else:
                    remaining.append(post)
                    
            with open(pending_file, "w") as pf:
                json.dump(remaining, pf)
                
            if uploaded_any:
                try:
                    from memory.saver import push_memory_to_github
                    push_memory_to_github()
                except Exception as e:
                    log(f"⚠️ Failed to push updated IG queue to GitHub: {e}")
                    
            exit(0)
            
        elif args.fresh:
            from memory.state_manager import get_state, start_fresh_run, set_active_render, mark_posted, mark_skipped, mark_failed
            from telegram.approver import notify_pipeline_started, notify_pipeline_skipped, notify_pipeline_failed
            
            state = get_state()
            if state["status"] in ("posted", "running"):
                msg = f"Pipeline is already '{state['status']}' for today. No new run started."
                log(f"⏭️ {msg}")
                notify_pipeline_skipped(msg)
                exit(0)
            
            start_fresh_run()
            notify_pipeline_started("Fresh Run", state["current_day"])
            
            try:
                fmt_list = ["1", "2", "3", "4"] if args.format == "all" else [args.format]
                results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=False, mock=args.mock, fmt_list=fmt_list, resume_only=False)
                
                is_rendering = any(res.get("rendering") for res in results.values())
                if is_rendering:
                    set_active_render(True)
                else:
                    posted_any = any(res.get("result", {}).get("url") for res in results.values())
                    if posted_any:
                        mark_posted()
                    else:
                        mark_skipped("Pipeline finished but no format was uploaded.")
            except Exception as e:
                import traceback
                mark_failed(str(e))
                notify_pipeline_failed(str(e), "Check logs and resolve error.")
                log(traceback.format_exc())
                exit(1)

        elif args.resume_check:
            from memory.state_manager import (
                get_state, set_active_render, mark_posted, mark_skipped,
                mark_failed, start_fresh_run, can_retry_today, has_active_nblm_state
            )
            from telegram.approver import notify_pipeline_failed, notify_pipeline_started, notify_pipeline_skipped
            from datetime import datetime, timezone
            import os

            state = get_state()
            memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")

            # ── Priority 1: Check nblm_state files (primary truth for active renders)
            if has_active_nblm_state(memory_dir):
                log("⏳ Active NotebookLM render state files detected. Resuming pipeline...")
                if state["status"] != "running":
                    start_fresh_run()
                set_active_render(True)
                try:
                    fmt_list = ["1", "2", "3", "4"] if args.format == "all" else [args.format]
                    results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=True, mock=args.mock, fmt_list=fmt_list, resume_only=True)
                    is_rendering = any(res.get("rendering") for res in results.values())
                    if is_rendering:
                        set_active_render(True)
                    else:
                        posted_formats_this_run = [fmt_id for fmt_id, res in results.items() if res.get("result", {}).get("url")]
                        if posted_formats_this_run:
                            for pf in posted_formats_this_run:
                                mark_posted(pf)
                        else:
                            mark_skipped("Resume completed but no format was uploaded.")
                except Exception as e:
                    import traceback
                    mark_failed(str(e))
                    notify_pipeline_failed(str(e), "Check NotebookLM generation or logs.")
                    log(traceback.format_exc())
                exit(0)

            # ── Priority 2: Normal resume via state manager (active_render flag)
            if state["status"] == "running" and state.get("active_render"):
                log("⏳ Active render state detected in pipeline_state.json. Resuming pipeline...")
                try:
                    fmt_list = ["1", "2", "3", "4"] if args.format == "all" else [args.format]
                    results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=True, mock=args.mock, fmt_list=fmt_list, resume_only=True)
                    is_rendering = any(res.get("rendering") for res in results.values())
                    if is_rendering:
                        set_active_render(True)
                    else:
                        posted_formats_this_run = [fmt_id for fmt_id, res in results.items() if res.get("result", {}).get("url")]
                        if posted_formats_this_run:
                            for pf in posted_formats_this_run:
                                mark_posted(pf)
                        else:
                            mark_skipped("Resume completed but no format was uploaded.")
                except Exception as e:
                    import traceback
                    mark_failed(str(e))
                    notify_pipeline_failed(str(e), "Check NotebookLM generation or logs.")
                    log(traceback.format_exc())
                exit(0)

            # ── Zombie State Timeout Check ──
            if state["status"] == "running" and state.get("last_updated"):
                try:
                    last_updated = datetime.fromisoformat(state["last_updated"])
                    minutes_since_update = (datetime.now(timezone.utc) - last_updated).total_seconds() / 60
                    if minutes_since_update > 60:
                        log(f"🧟 Zombie State Detected! Process has been 'running' for {minutes_since_update:.1f} minutes without updates. Resetting to failed...")
                        mark_failed("Zombie State Timeout (Hard Crash)")
                        state = get_state() # Reload state so Priority 3 can retry it
                except Exception as e:
                    pass

            # ── Priority 3: Time-Window Dispatcher
            utc_hour = datetime.now(timezone.utc).hour
            completed_formats = state.get("posted_formats", []) + state.get("exhausted_formats", [])
            
            from config import DAILY_REELS
            reels_count = args.daily_reels if args.daily_reels is not None else DAILY_REELS
            reels_count = max(1, min(6, reels_count))
            schedule_mapping = get_schedule_mapping(reels_count)
            
            target_fmt = None
            for fmt_id, target_hour in schedule_mapping:
                # E.g. "1" or "1_2"
                if fmt_id not in completed_formats and utc_hour >= target_hour:
                    target_fmt = fmt_id
                    break
                
            status_allows_retry = state["status"] in ("pending", "failed")
            
            if target_fmt and status_allows_retry:
                if can_retry_today(target_fmt):
                    retry_counts = state.get("retry_counts", {})
                    retry_num = retry_counts.get(target_fmt, 0) + 1
                    
                    if state["status"] == "failed":
                        log(f"⚠️ Previous run failed. Retry attempt {retry_num}/3 for Format {target_fmt} today...")
                    else:
                        log(f"⏰ Time window open! Starting fresh pipeline for Format {target_fmt}.")
                    
                    start_fresh_run(target_fmt)
                    notify_pipeline_started(f"Fresh Run (Format {target_fmt})", state["current_day"])
                    try:
                        fmt_list = [target_fmt]
                        results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=False, mock=args.mock, fmt_list=fmt_list, resume_only=False)
                        
                        is_rendering = any(res.get("rendering") for res in results.values())
                        if is_rendering:
                            set_active_render(True)
                        else:
                            posted_formats_this_run = [fmt_id for fmt_id, res in results.items() if res.get("result", {}).get("url")]
                            if posted_formats_this_run:
                                for pf in posted_formats_this_run:
                                    mark_posted(pf)
                            else:
                                mark_skipped(f"Pipeline finished but Format {target_fmt} was not uploaded.", target_fmt)
                    except Exception as e:
                        import traceback
                        if not can_retry_today(target_fmt):
                            from memory.state_manager import mark_exhausted
                            mark_exhausted(target_fmt, str(e))
                            notify_pipeline_failed(str(e), f"Format {target_fmt} failed 3 times and is permanently skipped for today.")
                        else:
                            mark_failed(str(e))
                            notify_pipeline_failed(str(e), f"Format {target_fmt} failed. Check logs.")
                        log(traceback.format_exc())
                    exit(0)

            # ── No action needed
            if state["status"] == "posted":
                log(f"✅ All formats posted today ({state.get('posted_formats', [])}). Nothing to do.")
            elif state["status"] == "failed":
                log(f"❌ Target format {target_fmt} exhausted its 3 retries. Moving to next window.")
                notify_pipeline_skipped(f"Max retries exhausted for Format {target_fmt}.")
            else:
                log(f"⏭️ No active render or pending run. Status: {state['status']}. Resume check taking no action.")
            exit(0)
        else:
            # Normal run
            for i in range(args.count):
                if args.count > 1:
                    log(f"\n{'='*60}\n▶ Pipeline Run {i+1}/{args.count}\n{'='*60}")
                
                fmt_list = ["1", "2", "3", "4"] if args.format == "all" else [args.format]
                run_all_formats(upload, niche=args.niche, manual=args.manual, resume=args.resume, mock=args.mock, fmt_list=fmt_list, resume_only=args.resume_only)
