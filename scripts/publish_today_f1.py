import os
import json
import logging
from uploader.youtube import upload_video
from main import handle_ig_upload
from analytics.tracker import log_upload
from memory.content_log import add_used_topic
from memory.state_manager import mark_posted
from telegram.approver import notify_pipeline_success

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

state_file = "memory/nblm_state_f1.json"
with open(state_file, "r") as f:
    state = json.load(f)

script_data = state["script_data"]
video_path = os.path.abspath("memory/notebooklm_f1_1792133784.mp4")
thumb_path = os.path.abspath("memory/notebooklm_f1_1792133784_thumb.jpg")

print(f"🎬 Uploading Format 1 to YouTube Shorts...")
print(f"   Title: {script_data['title']}")
print(f"   Video: {video_path}")
print(f"   Thumb: {thumb_path}")

# 1. YouTube Upload
yt_result = upload_video(
    video_path=video_path,
    title=script_data["title"],
    description=script_data["description"],
    hashtags=script_data["hashtags"],
    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
    is_short=True,
    schedule_time=None
)

yt_url = yt_result.get("url")
video_id = yt_result.get("video_id")
print(f"✅ YouTube Live: {yt_url} (ID: {video_id})")

if video_id:
    log_upload(video_id, 1, script_data.get("chosen_topic", ""), script_data.get("hook_angle", ""))
    add_used_topic(script_data.get("chosen_topic", ""), 1)

# 2. Instagram Upload / Queue
print(f"📸 Uploading to Instagram Reels...")
ig_post_id = None
try:
    ig_post_id = handle_ig_upload(script_data, video_path, None, "1")
    print(f"✅ Instagram Post ID: {ig_post_id}")
except Exception as e:
    print(f"⚠️ Instagram upload error: {e}")

# 3. Mark as posted and notify Telegram
mark_posted("1")
try:
    notify_pipeline_success("1", script_data["title"], yt_url, ig_post_id)
except Exception as e:
    print(f"⚠️ Telegram notify error: {e}")

print("🎉 Format 1 published successfully!")
