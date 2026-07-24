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
from video.notebooklm_footage import fetch_notebooklm_footage
from video.captions import transcribe_audio
from video.editor import build_video
from uploader.youtube import upload_video
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

def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False) -> dict:
    fmt = "1"
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 1, "skipped": True}

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
                    _clean_temp_for_format(1)
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
            import json
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
                    is_short=True
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 1, script_data.get("chosen_topic", ""), script_data.get("hook_angle", ""))
                add_used_topic(script_data.get("chosen_topic", ""), 1)
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                log("📸 Uploading to Instagram Reels...", fmt)
                caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(1)
        
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

def run_format2(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False) -> dict:
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
        if was_format_uploaded_today(2):
            log("⏭️  Format 2 already uploaded today. Skipping.", fmt)
            return {"format": 2, "skipped": True}

    log(f"🚀 Starting The Butterfly Effect | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(2)

    script_path  = os.path.join(TEMP_DIR, "script_f2.json")
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
                    _clean_temp_for_format(2)
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
            import json
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
                    is_short=True
                )
                log(f"   ✅ Live: {result['url']}", fmt)
                
                # Post-upload tracking
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 2, script_data["title"], script_data["hook"])
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 2)
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                log("📸 Uploading to Instagram Reels...", fmt)
                caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
                
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(2)

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

def run_format3(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False) -> dict:
    fmt = "3"
    log("━" * 50, fmt)
    
    state_path = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if resume_only and not os.path.exists(state_path):
        log("⏭️  No active generation state found and resume-only is active. Skipping.", fmt)
        return {"format": 3, "skipped": True}

    if upload:
        from analytics.tracker import was_format_uploaded_today
        if was_format_uploaded_today(3):
            log("⏭️  Format 3 already uploaded today. Skipping.", fmt)
            return {"format": 3, "skipped": True}

    log(f"🚀 Starting Everyday Brain Glitches | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(3)

    script_path  = os.path.join(TEMP_DIR, "script_f3.json")
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
                    _clean_temp_for_format(3)
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
            import json
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
                    is_short=True
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 3, script_data["dilemma_seed"], script_data.get("closing_question", ""))
                add_used_topic(script_data["dilemma_seed"], 3)
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                log("📸 Uploading to Instagram Reels...", fmt)
                caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
            
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(3)

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

def run_format4(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False) -> dict:
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
        if was_format_uploaded_today(4):
            log("⏭️  Format 4 already uploaded today. Skipping.", fmt)
            return {"format": 4, "skipped": True}

    log(f"🚀 Starting Genius Loopholes Case study | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(4)

    script_path  = os.path.join(TEMP_DIR, "script_f4.json")

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
                    _clean_temp_for_format(4)
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
            import json
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
                    is_short=True
                )
                log(f"   ✅ YouTube Live: {result['url']}", fmt)
                
                # Post-upload tracking
                from analytics.tracker import log_upload
                from memory.content_log import add_used_topic
                if "video_id" in result:
                    log_upload(result["video_id"], 4, script_data["title"], script_data.get("hook", ""))
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 4)
                
                with open(yt_tracker, "w") as f:
                    json.dump(result, f)

            from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID
            if IG_ACCESS_TOKEN and IG_ACCOUNT_ID:
                log("📸 Uploading to Instagram Reels...", fmt)
                caption = f"{script_data['title']}\n\n{script_data.get('description', '')}\n\n" + " ".join(script_data['hashtags'])
                ig_post_id = upload_reel(video_path, caption, IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
                result["ig_post_id"] = ig_post_id
            if os.path.exists(yt_tracker):
                os.remove(yt_tracker)
                
        else:
            log("⏭️  Step 7/7: Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(4)

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


def run_format5(upload: bool = True, attempt: int = 1, resume: bool = False, mock: bool = False, resume_only: bool = False):
    """
    Format 5: Long-Form Cinematic Widescreen Video.
    Generated on a 2-day schedule.
    """
    from generator.script import generate_long_video
    from video.notebooklm_footage import fetch_notebooklm_footage
    from uploader.youtube import upload_video
    fmt = 5
    state_path = os.path.join(TEMP_DIR, "memory", f"nblm_state_f{fmt}.json")
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
        _clean_temp_for_format(5)

    script_path  = os.path.join(TEMP_DIR, "script_f5.json")

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
                    _clean_temp_for_format(5)
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
        cleanup_notebooklm_state(5)

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

def run_all_formats(upload: bool = True, niche: str = None, manual: bool = False, resume: bool = False, mock: bool = False, fmt_list=["1", "2", "3", "4"], resume_only: bool = False):
    """
    Run all formats in quota-priority order (F1 → F2 → F3 → F4).
    Skips remaining formats if Gemini quota runs out.
    """
    log("━" * 50)
    log(f"▶▶ Running formats | {quota_tracker.status()}")

    runners = []
    if "all" in fmt_list or "1" in fmt_list:
        runners.append(("1", lambda attempt=1: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only)))
    if "all" in fmt_list or "2" in fmt_list:
        runners.append(("2", lambda attempt=1: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only)))
    if "all" in fmt_list or "3" in fmt_list:
        runners.append(("3", lambda attempt=1: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only)))
    if "all" in fmt_list or "4" in fmt_list:
        runners.append(("4", lambda attempt=1: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only)))

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
    if pipeline_has_errors:
        raise RuntimeError("One or more formats failed completely.")
    return results


# ── Scheduler ─────────────────────────────────────────────────────────────────

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

    # Run the powerful Time-Window Dispatcher every 15 minutes
    # It will automatically detect if it's time for a new format, or if it needs to retry a failed one!
    def tick_dispatcher():
        import subprocess
        print("⏰ Scheduler Tick: Triggering Dispatcher Check...")
        subprocess.run(["python", "main.py", "resume-check"])

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
        if args.fresh:
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

            # ── Priority 3: Time-Window Dispatcher
            utc_hour = datetime.now(timezone.utc).hour
            completed_formats = state.get("posted_formats", []) + state.get("exhausted_formats", [])
            
            target_fmt = None
            if "1" not in completed_formats and utc_hour >= 9:
                target_fmt = "1"
            elif "2" not in completed_formats and utc_hour >= 13:
                target_fmt = "2"
            elif "3" not in completed_formats and utc_hour >= 17:
                target_fmt = "3"
            elif "4" not in completed_formats and utc_hour >= 21:
                target_fmt = "4"
                
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
