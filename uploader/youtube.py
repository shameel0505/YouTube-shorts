import os
import sys
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config import YOUTUBE_CLIENT_SECRET, YOUTUBE_TOKEN_FILE, YT_CATEGORY_ID, YT_DEFAULT_TAGS, YT_PRIVACY

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def _get_youtube_client():
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"⚠️ Could not load token: {e}")

    if not creds or not creds.valid:
        is_headless = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("RENDER") == "true" or not sys.stdin.isatty()
        
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Refresh token failed: {e}. Re-authenticating...")
                if is_headless:
                    raise RuntimeError(
                        "YouTube OAuth token expired and cannot be refreshed in a headless environment. "
                        "Please run the script locally on your computer to re-authenticate, then update TOKEN_JSON in GitHub secrets."
                    )
                if os.path.exists(YOUTUBE_TOKEN_FILE):
                    try:
                        os.remove(YOUTUBE_TOKEN_FILE)
                    except:
                        pass
                flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRET, SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            if is_headless:
                raise RuntimeError(
                    "YouTube OAuth credentials are missing or invalid in a headless environment. "
                    "Please run the script locally on your computer to authenticate first, then update TOKEN_JSON in GitHub secrets."
                )
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(YOUTUBE_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
            
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path: str, title: str, description: str, hashtags: list, schedule_time: datetime = None, thumbnail_path: str = None, is_short: bool = True) -> dict:
    youtube = _get_youtube_client()
    
    full_description = f"{description}\n\n{' '.join(hashtags)}"
    if is_short:
        full_description += "\n\n#shorts"
        
    privacy = YT_PRIVACY
    publish_at = None
    
    if schedule_time:
        privacy = "private"
        publish_at = schedule_time.isoformat()
        
    body = {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": YT_DEFAULT_TAGS + [t.lstrip("#") for t in hashtags],
            "categoryId": YT_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }
    
    if publish_at:
        body["status"]["publishAt"] = publish_at
        
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5*1024*1024)
    print("🚀 Initiating YouTube upload...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress()*100)}%", end="\r")
        except HttpError as e:
            print(f"\n❌ YouTube Upload HttpError: {e}")
            raise
            
    video_id = response["id"]
    url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"\n✅ Uploaded! {url}")
    
    if thumbnail_path and os.path.exists(thumbnail_path):
        _upload_thumbnail(youtube, video_id, thumbnail_path)
        
    return {"video_id": video_id, "url": url}

def _upload_thumbnail(youtube, video_id: str, thumbnail_path: str):
    try:
        youtube.thumbnails().set(
            videoId=video_id, 
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        ).execute()
        print("✅ Thumbnail uploaded")
    except HttpError as e:
        print(f"⚠️ Thumbnail upload failed: {e}")

def get_next_upload_time(hour: int = 9, minute: int = 0) -> datetime:
    now = datetime.now(timezone.utc)
    next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_time <= now:
        next_time += timedelta(days=1)
    return next_time
