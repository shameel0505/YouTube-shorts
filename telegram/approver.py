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

def _send_video(video_path: str, caption: str, reply_markup: dict = None) -> int:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    with open(video_path, "rb") as f:
        files = {"video": f}
        resp = requests.post(url, data=data, files=files).json()
    if resp.get("ok"):
        return resp["result"]["message_id"]
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
