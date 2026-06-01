import os
from dotenv import load_dotenv

load_dotenv()

# Google / Gemini
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY")
GCP_PROJECT_ID        = os.getenv("GCP_PROJECT_ID")
GCP_REGION            = os.getenv("GCP_REGION", "us-central1")
GCS_BUCKET            = os.getenv("GCS_BUCKET")

# YouTube
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET_JSON", "./client_secret.json")
YOUTUBE_TOKEN_FILE    = os.getenv("YOUTUBE_TOKEN_FILE", "token.json")

# Pexels (kept for compatibility)
PEXELS_API_KEY        = os.getenv("PEXELS_API_KEY")
BRAVE_API_KEY         = os.getenv("BRAVE_API_KEY")

# Instagram
IG_ACCESS_TOKEN       = os.getenv("IG_ACCESS_TOKEN")
IG_ACCOUNT_ID         = os.getenv("IG_ACCOUNT_ID")

# Content
NICHE                 = os.getenv("NICHE", "mind-blowing facts")
SHORTS_PER_DAY        = int(os.getenv("SHORTS_PER_DAY", "1"))
VIDEO_DURATION_SEC    = int(os.getenv("VIDEO_DURATION_SEC", "55"))
OUTPUT_DIR            = os.getenv("OUTPUT_DIR", "./output")
TEMP_DIR              = os.getenv("TEMP_DIR", "./temp")

# ── Kokoro FastAPI TTS (replaces Google Cloud TTS) ───────────────────────────
KOKORO_API_URL        = os.getenv("KOKORO_API_URL", "http://localhost:8880")
KOKORO_VOICE          = os.getenv("KOKORO_VOICE", "af_heart")

PEXELS_API_KEY        = os.getenv("PEXELS_API_KEY", "")

# Video dimensions — Shorts are always 1080x1920 (9:16 vertical)
VIDEO_WIDTH           = 1080
VIDEO_HEIGHT          = 1920
VIDEO_FPS             = 30

# ── Final export settings (change here, never in editor code) ─────────────────
VIDEO_CODEC           = "libx264"
AUDIO_CODEC           = "aac"
VIDEO_BITRATE         = "8000k"
AUDIO_BITRATE         = "192k"
VIDEO_MIN_FPS         = 30
EXPORT_PRESET         = "fast"
EXPORT_THREADS        = 4

# Caption appearance
CAPTION_FONT_SIZE        = 80
CAPTION_STROKE_WIDTH     = 6       # updated to 6px per spec
CAPTION_COLOR            = "white"
CAPTION_STROKE_COLOR     = "black"
CAPTION_HOOK_MULTIPLIER  = 1.2    # first-frame hook text is 120% of normal size

# Pill background behind captions
PILL_PADDING_X  = 12
PILL_PADDING_Y  = 8
PILL_RADIUS     = 14
PILL_COLOR_RGBA = (0, 0, 0, 160)  # semi-transparent dark

# Per-format caption highlight colors
HIGHLIGHT_COLOR = {1: "#FFE600", 2: "#FF2222", 3: "#66CCFF"}

# Background clip segmentation (cuts every 1.5–2.5 seconds)
CLIP_SEGMENT_MIN_DUR = 1.5
CLIP_SEGMENT_MAX_DUR = 2.5

# Opening title card
TITLE_CARD_DURATION    = 1.0   # seconds the title card is shown
PART_LABEL_FADE_TIME   = 3.0   # Format 2 corner label fades after this many seconds

# Format 3 closing question overlay
CLOSING_Q_DURATION     = 5.0
CLOSING_Q_FONT_SIZE    = 120
CLOSING_Q_BG_ALPHA     = 210
CLOSING_Q_STROKE_WIDTH = 10

# Progress bar (Format 2 only)
PROGRESS_BAR_HEIGHT    = 8
PROGRESS_BAR_OPACITY   = 0.60   # 60% opacity white

# Audio levels
MUSIC_VOLUME           = 0.15   # 15% under voice per spec
AUDIO_TARGET_LUFS      = -14    # normalize output to -14 LUFS

TELEGRAM_BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID")

# ── Asset folder paths ────────────────────────────────────────────────────────
GAMEPLAY_DIR           = "./gameplay"
ASSETS_MUSIC_DIR       = "./assets/music"
ASSETS_SFX_DIR         = "./assets/sfx"
ASSETS_IMAGES_DIR      = "./assets/images"

# Legacy — kept for compatibility (overridden by MUSIC_VOLUME above)
BACKGROUND_MUSIC_PATH  = os.getenv("BACKGROUND_MUSIC_PATH", "")

# YouTube defaults
YT_CATEGORY_ID        = "28"   # Science & Technology
YT_DEFAULT_TAGS       = ["shorts", "facts", "didyouknow", "technology", "AI"]
YT_PRIVACY            = os.getenv("YT_PRIVACY", "public")

# Gemini
GEMINI_MODEL          = "gemini-2.5-flash"

# ── Scheduler — posting times in UTC ─────────────────────────────────────────
FORMAT1_SCHEDULE_HOUR = int(os.getenv("FORMAT1_SCHEDULE_HOUR", "9"))   # Facts
FORMAT2_SCHEDULE_HOUR = int(os.getenv("FORMAT2_SCHEDULE_HOUR", "13"))  # Thriller
FORMAT3_SCHEDULE_HOUR = int(os.getenv("FORMAT3_SCHEDULE_HOUR", "17"))  # Dilemma

# ── Quota management ─────────────────────────────────────────────────────────
GEMINI_QUOTA_LIMIT    = 20
GEMINI_QUOTA_FILE     = os.path.join(TEMP_DIR, "gemini_quota.json")

# ── Story state (Format 2 — Serialized Thriller) ─────────────────────────────
STORY_STATE_FILE      = os.path.join(TEMP_DIR, "story_state.json")

# ── Create dirs on import ─────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs("./logs", exist_ok=True)

# Asset subfolders
for _d in [
    "./gameplay/facts", "./gameplay/thriller", "./gameplay/dilemma",
    "./assets/music/facts", "./assets/music/thriller", "./assets/music/dilemma",
    "./assets/sfx",
    "./assets/images/facts",
]:
    os.makedirs(_d, exist_ok=True)
