import os
import json
import datetime
from google.cloud import storage

BUCKET_NAME = "shameel-ai-shorts-bucket"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

blob_name = "format_1_2026-07-28_rescue.mp4"
blob = bucket.blob(blob_name)
print(f"Uploading {blob_name} to GCS...")
blob.upload_from_filename("/Users/shameel/Desktop/youtube/experiments/videos/Your Memories Are Lying to You.MP4")

signed_url = blob.generate_signed_url(
    version="v4",
    expiration=datetime.timedelta(days=7),
    method="GET"
)
print(f"✅ Uploaded! URL: {signed_url}")

caption = "Your Memories Are Lying to You 🤯\n\nThink your memories are a perfect recording of the past? Think again! Every time you recall a memory, your brain is actually *re-writing* it. It's called memory reconsolidation, and it means your most vivid recollections might be slightly (or completely!) wrong. 🧠✨\n\nEvery telling changes the tale, adding details that weren't there or erasing what was. It’s like playing a lifelong game of telephone with yourself! ☎️ So next time you're absolutely certain about how something happened, remember: your brain might be the ultimate storyteller.\n\nWhat’s a childhood memory you later found out was totally inaccurate? Drop it in the comments! 👇\n\n#shorts #psychology #memory #brainfacts #science #mindblown #cognitivebias"

with open('memory/pending_ig.json', 'r') as f:
    pending = json.load(f)

new_item = {
    "url": signed_url,
    "caption": caption,
    "schedule_time": "2026-07-28T09:00:00+00:00",
    "fmt": "1"
}
pending.insert(0, new_item)

with open('memory/pending_ig.json', 'w') as f:
    json.dump(pending, f)
print("✅ memory/pending_ig.json updated successfully!")
