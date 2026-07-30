import os
import json
import datetime
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"
client = storage.Client()
old_bucket = client.bucket("shameel-ai-shorts-bucket")
new_bucket = client.bucket("shameel-shorts-free-tier-bucket")

# 1. Copy files
blobs = list(old_bucket.list_blobs())
for blob in blobs:
    print(f"Copying {blob.name}...")
    new_blob = old_bucket.copy_blob(blob, new_bucket, blob.name)
    # 2. Delete from old bucket
    blob.delete()
    print(f"Deleted {blob.name} from old bucket.")

# 3. Update pending_ig.json signed URLs
pending_path = "memory/pending_ig.json"
if os.path.exists(pending_path):
    with open(pending_path) as f:
        data = json.load(f)
    
    for item in data:
        if "shameel-ai-shorts-bucket" in item.get("url", ""):
            # We need to extract the blob name from the URL
            # URL format: https://storage.googleapis.com/shameel-ai-shorts-bucket/format_1_2026-07-29.mp4?...
            try:
                blob_name = item["url"].split("shameel-ai-shorts-bucket/")[1].split("?")[0]
                new_blob = new_bucket.blob(blob_name)
                # Generate new signed URL
                signed_url = new_blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(days=7),
                    method="GET"
                )
                item["url"] = signed_url
                print(f"Updated signed URL for {blob_name}")
            except Exception as e:
                print(f"Failed to update URL for {item['url']}: {e}")
                
    with open(pending_path, "w") as f:
        json.dump(data, f, indent=4)
    print("Updated memory/pending_ig.json")

