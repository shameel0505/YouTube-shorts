import os
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"
client = storage.Client()
bucket_name = "shameel-shorts-free-tier-bucket"

try:
    bucket = client.bucket(bucket_name)
    new_bucket = client.create_bucket(bucket, location="us-central1")
    print(f"✅ Created bucket {new_bucket.name} in {new_bucket.location}")
    
    # Add 3 day lifecycle rule
    bucket.add_lifecycle_delete_rule(age=3)
    bucket.patch()
    print("✅ Added 3-day deletion lifecycle rule.")
except Exception as e:
    print(f"Error: {e}")
