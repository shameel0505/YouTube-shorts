import time
import requests
import logging
import os
import datetime
from pathlib import Path
from google.cloud import storage

log = logging.getLogger(__name__)

class MultiProviderUploader:
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}

    def _upload_gcs(self, path: Path) -> str:
        # Load bucket name from env (default to the user's bucket)
        bucket_name = os.environ.get("GCS_BUCKET", "shameel-ai-shorts-bucket")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Ensure bucket exists and has 3-day deletion lifecycle (idempotent)
        try:
            if not bucket.lifecycle_rules:
                rule = {"action": {"type": "Delete"}, "condition": {"age": 3}}
                bucket.lifecycle_rules = [rule]
                bucket.patch()
                log.info(f"Applied 3-day deletion lifecycle to {bucket_name}")
        except Exception as e:
            log.warning(f"Could not verify bucket lifecycle: {e}")
            
        blob_name = f"video_{int(time.time())}.mp4"
        blob = bucket.blob(blob_name)
        
        log.info(f"Uploading {path.name} to GCS ({bucket_name}/{blob_name})...")
        blob.upload_from_filename(str(path))
        
        # Generate Signed URL valid for 7 days
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(days=7),
            method="GET"
        )
        
        log.info(f"GCS Upload complete. Signed URL generated.")
        return signed_url

    def _upload_catbox(self, path: Path) -> str:
        with open(path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                headers=self.HEADERS,
                timeout=300,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"catbox.moe returned no URL: {url}")
        return url

    def _upload_litterbox(self, path: Path) -> str:
        with open(path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": f},
                headers=self.HEADERS,
                timeout=300,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"litterbox returned unexpected response: {url!r}")
        return url

    def upload(self, path: Path, raise_on_failure: bool = True) -> str:
        providers = [
            ("gcs", self._upload_gcs),
            ("litterbox", self._upload_litterbox),
            ("catbox.moe", self._upload_catbox),
        ]
        last_exc = None
        for name, fn in providers:
            try:
                url = fn(path)
                return url
            except Exception as e:
                last_exc = e

        if raise_on_failure:
            raise RuntimeError(f"All video upload providers failed for {path.name}. Last error: {last_exc}")
        return None

class MetaInstagramAPI:
    def __init__(self, access_token: str, ig_account_id: str, api_version: str = "v21.0"):
        self.token = access_token
        self.account_id = ig_account_id
        self.base = f"https://graph.facebook.com/{api_version}"

    def _get(self, endpoint, **params):
        time.sleep(2)
        params["access_token"] = self.token
        r = requests.get(f"{self.base}/{endpoint}", params=params, timeout=15)
        if not r.ok:
            try:
                err_data = r.json()
                msg = f"Graph API Error: {r.status_code} - {err_data.get('error', {}).get('message', r.text)}"
            except:
                msg = f"Graph API Error: {r.status_code} - {r.text}"
            raise RuntimeError(msg)
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Graph API error: {data['error']}")
        return r.status_code, data

    def _post(self, endpoint, **params):
        time.sleep(2)
        query = {"access_token": self.token}
        r = requests.post(f"{self.base}/{endpoint}", params=query, data=params, timeout=45)
        if not r.ok:
            try:
                err_data = r.json()
                msg = f"Graph API Error: {r.status_code} - {err_data.get('error', {}).get('message', r.text)}"
            except:
                msg = f"Graph API Error: {r.status_code} - {r.text}"
            raise RuntimeError(msg)
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Graph API error: {data['error']}")
        return r.status_code, data

    def create_reel_container(self, video_url: str, caption: str) -> tuple:
        status, result = self._post(
            f"{self.account_id}/media",
            media_type="REELS",
            video_url=video_url,
            caption=caption,
            share_to_feed="true"
        )
        return status, str(result["id"])

    def check_container_status(self, container_id: str) -> str:
        status, result = self._get(container_id, fields="status_code")
        return result.get("status_code", "UNKNOWN")

    def publish(self, container_id: str) -> tuple:
        status, result = self._post(
            f"{self.account_id}/media_publish",
            creation_id=container_id,
        )
        return status, str(result["id"])

def get_public_url(video_path: str) -> str:
    print("   ↑ Uploading MP4 to temporary public host...")
    uploader = MultiProviderUploader()
    public_url = uploader.upload(Path(video_path))
    print(f"   ⬡ Public URL ready: {public_url}")
    return public_url

def publish_from_url(public_url: str, caption: str, access_token: str, account_id: str) -> str:
    api = MetaInstagramAPI(access_token, account_id)
    
    print("   ⬡ Creating Reels container...")
    _, container_id = api.create_reel_container(public_url, caption)
    print(f"   ✅ Reels container created: {container_id}")
    
    print("   ⏳ Waiting for Instagram to process the video...")
    ready = False
    for attempt in range(48):
        status = api.check_container_status(container_id)
        print(f"      ⬡ Container Status: {status}")
        if status == "FINISHED":
            ready = True
            break
        elif status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing (status ERROR)")
        time.sleep(10)
        
    if not ready:
        raise RuntimeError(f"Container {container_id} not FINISHED after 480s")
        
    print("   ⏳ Publishing Reel...")
    _, post_id = api.publish(container_id)
    print(f"   ✅ Successfully posted to Instagram Reels! ID = {post_id}")
    return post_id

def upload_reel(video_path: str, caption: str, access_token: str, account_id: str) -> str:
    public_url = get_public_url(video_path)
    return publish_from_url(public_url, caption, access_token, account_id)
