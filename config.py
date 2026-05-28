import os
from dotenv import load_dotenv

load_dotenv()

# Google / Gemini
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY")
GCP_PROJECT_ID        = os.getenv("GCP_PROJECT_ID")
GCP_REGION            = os.getenv("GCP_REGION", "us-central1")
GCS_BUCKET            = os.getenv("GCS_BUCKET")
GOOGLE_CREDS_JSON     = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# YouTube
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET_JSON", "./client_secret.json")
YOUTUBE_TOKEN_FILE    = os.getenv("YOUTUBE_TOKEN_FILE", "token.json")

# Pexels
PEXELS_API_KEY        = os.getenv("PEXELS_API_KEY")

# Content
NICHE                 = os.getenv("NICHE", "AI and technology facts")
SHORTS_PER_DAY        = int(os.getenv("SHORTS_PER_DAY", "1"))
VIDEO_DURATION_SEC    = int(os.getenv("VIDEO_DURATION_SEC", "55"))
OUTPUT_DIR            = os.getenv("OUTPUT_DIR", "./output")
TEMP_DIR              = os.getenv("TEMP_DIR", "./temp")

# TTS
TTS_VOICE_NAME        = os.getenv("TTS_VOICE_NAME", "en-US-Neural2-D")
TTS_LANGUAGE_CODE     = os.getenv("TTS_LANGUAGE_CODE", "en-US")
TTS_SPEAKING_RATE     = float(os.getenv("TTS_SPEAKING_RATE", "1.05"))

# Video dimensions — Shorts are always 1080x1920 (9:16 vertical)
VIDEO_WIDTH           = 1080
VIDEO_HEIGHT          = 1920
VIDEO_FPS             = 30

# Caption appearance
CAPTION_FONT_SIZE     = 70
CAPTION_COLOR         = "white"
CAPTION_STROKE_COLOR  = "black"
CAPTION_STROKE_WIDTH  = 3

# YouTube defaults
YT_CATEGORY_ID        = "28"   # Science & Technology
YT_DEFAULT_TAGS       = ["shorts", "facts", "didyouknow", "technology", "AI"]
YT_PRIVACY            = os.getenv("YT_PRIVACY", "public")

# Gemini
GEMINI_MODEL          = "gemini-2.0-flash"

# Background music
BACKGROUND_MUSIC_PATH = os.getenv("BACKGROUND_MUSIC_PATH", "")
MUSIC_VOLUME          = 0.08   # very quiet under voice

# Create dirs on import
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs("./logs", exist_ok=True)
