import os
from dotenv import load_dotenv
load_dotenv()
from uploader.instagram import upload_reel
from config import IG_ACCESS_TOKEN, IG_ACCOUNT_ID

video = "./output/short_f3_20260530_233410.mp4"
if os.path.exists(video):
    upload_reel(video, "Test IG Upload from Bot #shorts", IG_ACCESS_TOKEN, IG_ACCOUNT_ID)
else:
    print("Test video not found!")
