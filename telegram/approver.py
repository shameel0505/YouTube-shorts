import os
import time
import requests
import json
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def _send_message(text: str, reply_markup: dict = None) -> int:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    resp = requests.post(url, json=payload).json()
    if resp.get("ok"):
        return resp["result"]["message_id"]
    return None

def _send_photo(photo_url: str) -> int:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url}
    resp = requests.post(url, json=payload).json()
    if resp.get("ok"):
        return resp["result"]["message_id"]
    return None

def _get_video_meta(video_path: str):
    import subprocess
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json", video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)["streams"][0]
        w = int(data.get("width", 720))
        h = int(data.get("height", 1280))
        dur = int(float(data.get("duration", 0)))
        return w, h, dur
    except Exception:
        return 720, 1280, 0

def _send_video(video_path: str, caption: str, reply_markup: dict = None) -> int:
    import subprocess
    from pathlib import Path
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    w, h, dur = _get_video_meta(video_path)
    
    # Ensure dimensions match vertical shorts standard (9:16)
    if w > h and w == 1280 and h == 720:
        # Flipped orientation safety
        w, h = 720, 1280
        
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "HTML",
        "width": w,
        "height": h,
        "duration": dur,
        "supports_streaming": True,
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    # Telegram Bot API requirement: thumbnail max width & height is 320px.
    # For 9:16 vertical shorts, 180x320 is exact 9:16 aspect ratio (<320px limit).
    # Generating with exact setsar=1 prevents Telegram client from squishing the player.
    thumb_path = Path("/tmp") / f"tg_thumb_{int(time.time())}.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-ss", "00:00:01",
        "-i", video_path,
        "-vf", "scale=180:320:force_original_aspect_ratio=decrease,pad=180:320:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-vframes", "1",
        "-q:v", "2",
        str(thumb_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    f_vid = open(video_path, "rb")
    # Pass explicit filename and video/mp4 MIME type so Telegram demuxer parses stream parameters properly
    files = {
        "video": (Path(video_path).name, f_vid, "video/mp4")
    }
    f_thumb = None
    if thumb_path.exists() and thumb_path.stat().st_size > 0:
        f_thumb = open(thumb_path, "rb")
        # Support both 'thumbnail' (Bot API 6.6+) and legacy 'thumb' parameter
        files["thumbnail"] = ("thumb.jpg", f_thumb, "image/jpeg")

    try:
        resp = requests.post(url, data=data, files=files).json()
        if resp.get("ok"):
            return resp["result"]["message_id"]
        else:
            print(f"⚠️ Telegram sendVideo error: {resp}")
    finally:
        f_vid.close()
        if f_thumb:
            f_thumb.close()
            try:
                thumb_path.unlink()
            except Exception:
                pass
    return None

def _poll_for_callback(timeout: int, allowed_data: list = None) -> str:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    start_time = time.time()
    offset = None
    
    # Clear pending updates
    try:
        resp = requests.get(url, params={"offset": -1}).json()
        if resp.get("ok") and resp["result"]:
            offset = resp["result"][-1]["update_id"] + 1
    except:
        pass
        
    while time.time() - start_time < timeout:
        params = {"timeout": 10}
        if offset:
            params["offset"] = offset
            
        try:
            resp = requests.get(url, params=params, timeout=15).json()
            if resp.get("ok"):
                for update in resp["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"]
                        if allowed_data is None or "TEXT" in allowed_data:
                            return text

                    if "callback_query" in update:
                        data = update["callback_query"]["data"]
                        if not allowed_data or data in allowed_data:
                            # Answer callback query to stop loading circle
                            cb_id = update["callback_query"]["id"]
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})
                            return data
        except:
            pass
        time.sleep(1)
        
    return None

def wait_for_topic_approval(topics: list[dict], timeout=600) -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("   ⚠️ Telegram not configured. Auto-picking first topic.")
        return topics[0]
        
    text = "<b>Select a topic for script generation:</b>\n"
    text += "<i>(Or type a custom topic / Google Search query directly into this chat)</i>\n\n"
    keyboard = []
    for i, t in enumerate(topics):
        title = t.get('title') or t.get('dilemma_seed') or t.get('text') or f"Topic {i+1}"
        text += f"{i+1}. {title}\n"
        keyboard.append([{"text": f"Topic {i+1}", "callback_data": f"topic_{i}"}])
        
    _send_message(text, reply_markup={"inline_keyboard": keyboard})
    print(f"   ⏳ Waiting for Telegram topic approval (up to {timeout}s)...")
    
    allowed = [f"topic_{i}" for i in range(len(topics))]
    allowed.append("TEXT")
    
    choice = _poll_for_callback(timeout, allowed)
    
    if choice and choice.startswith("topic_"):
        idx = int(choice.split("_")[1])
        print(f"   ✅ Selected: {idx+1}")
        return topics[idx]
    elif choice:
        print(f"   ✅ Custom Topic/Query provided: {choice}")
        return {"text": choice, "chosen_topic": choice, "dilemma_seed": choice, "source": "Manual Telegram Input"}
        
    print("   ⚠️ Timeout waiting for topic. Defaulting to 1.")
    return topics[0]

def wait_for_image_approval(images: list[dict], timeout=600) -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return None
        
    print(f"   ⏳ Sending {len(images)} images to Telegram for approval...")
    for i, img in enumerate(images):
        _send_photo(img["src"]["large2x"])
        
    # Group buttons in chunks of 5
    keyboard = []
    row = []
    for i in range(len(images)):
        row.append({"text": f"Image {i+1}", "callback_data": f"img_{i}"})
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    _send_message("Select the best image:", reply_markup={"inline_keyboard": keyboard})
    
    choice = _poll_for_callback(timeout, [f"img_{i}" for i in range(len(images))])
    
    if choice:
        idx = int(choice.split("_")[1])
        print(f"   ✅ Selected: Image {idx+1}")
        return images[idx]
        
    print("   ⚠️ Timeout waiting for image. Defaulting to None.")
    return None

def wait_for_video_approval(video_path: str, caption: str, timeout=1800) -> str:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return "Approve"
        
    print(f"   ⏳ Sending video to Telegram for approval (up to {timeout}s)...")
    keyboard = [[
        {"text": "✅ Approve", "callback_data": "Approve"},
        {"text": "❌ Reject", "callback_data": "Reject"}
    ]]
    _send_video(video_path, caption, reply_markup={"inline_keyboard": keyboard})
    
    choice = _poll_for_callback(timeout, ["Approve", "Reject"])
    
    if choice == "Reject":
        followup_kb = [[
            {"text": "Regen Script", "callback_data": "Regenerate Script"},
            {"text": "Diff Topic", "callback_data": "Change Topic"},
            {"text": "Abort", "callback_data": "Abort"}
        ]]
        _send_message("Video rejected. What would you like to do?", reply_markup={"inline_keyboard": followup_kb})
        followup = _poll_for_callback(timeout, ["Regenerate Script", "Change Topic", "Abort"])
        return followup or "Abort"
        
    if choice == "Approve":
        return "Approve"
        
    print("   ⚠️ Timeout waiting for video approval. Skipping upload.")
    return "Timeout"

def send_telegram_notification(text: str) -> bool:
    """Sends an automated HTML-formatted notification to the user on Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram notification: {e}")
        return False

def notify_pipeline_started(mode: str, day: str) -> bool:
    text = f"🚀 <b>Daily pipeline started</b> for <code>{day}</code>.\nMode: <code>{mode}</code>.\nChecking pending topics..."
    return send_telegram_notification(text)

def notify_pipeline_running(format_num: str, script_title: str) -> bool:
    text = f"⏳ <b>Pipeline is waiting on NotebookLM render.</b>\nFormat <code>{format_num}</code>: <i>{script_title}</i>\nThe resume check will verify it in 15 minutes."
    return send_telegram_notification(text)

def notify_pipeline_success(format_num: str, title: str, yt_url: str, ig_id: str) -> bool:
    text = f"✅ <b>Daily Post Actually Uploaded!</b>\nFormat: <code>{format_num}</code>\nTitle: <i>{title}</i>\n"
    if yt_url:
        text += f"YouTube: <a href='{yt_url}'>Link</a>\n"
    if ig_id:
        text += f"Instagram: <code>{ig_id}</code>\n"
    else:
        text += "Instagram: ⚠️ Upload Failed/Skipped\n"
    return send_telegram_notification(text)

def notify_pipeline_failed(error_summary: str, action_needed: str) -> bool:
    safe_error = error_summary.replace("<", "&lt;").replace(">", "&gt;")
    text = f"❌ <b>Pipeline Failed</b>\nReason: <code>{safe_error}</code>\nNext Action: {action_needed}"
    return send_telegram_notification(text)

def notify_pipeline_skipped(reason: str) -> bool:
    safe_reason = reason.replace("<", "&lt;").replace(">", "&gt;")
    text = f"⏭️ <b>Pipeline Run Skipped</b>\nReason: <i>{safe_reason}</i>"
    return send_telegram_notification(text)
