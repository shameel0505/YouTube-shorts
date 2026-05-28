# 🤖 YouTube Shorts Bot

Fully automated YouTube Shorts pipeline using **100% Google/free APIs**.

```
Gemini 2.0 Flash → Google Neural2 TTS → Pexels footage → FFmpeg edit → YouTube upload
```

**Cost: $0/month** | Posts daily automatically via GCP Cloud Scheduler

---

## 📁 Project Structure

```
shorts_bot/
├── main.py                  ← Entry point
├── config.py                ← All settings
├── .env.example             ← Copy to .env and fill in
├── requirements.txt
├── Dockerfile
├── deploy_gcp.sh            ← One-command GCP deploy
├── generator/
│   ├── script.py            ← Gemini script writer
│   └── voiceover.py         ← Google Neural2 TTS
├── video/
│   ├── footage.py           ← Pexels downloader
│   ├── captions.py          ← Whisper transcription
│   └── editor.py            ← MoviePy/FFmpeg assembler
└── uploader/
    └── youtube.py           ← YouTube Data API v3
```

---

## 🔑 Step 1: Get Your API Keys (all free)

### Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Click **Create API Key**
3. Copy into `.env` as `GEMINI_API_KEY`

### Google Cloud (TTS + Storage)
1. Go to https://console.cloud.google.com
2. Create a project (or use existing)
3. Enable **Cloud Text-to-Speech API**
4. Go to **IAM → Service Accounts → Create**
5. Grant role: `Cloud Text-to-Speech User`
6. Download JSON key → save as `service-account.json`
7. Set path in `.env` as `GOOGLE_APPLICATION_CREDENTIALS=./service-account.json`

### Pexels API (free, 200 req/hr)
1. Go to https://www.pexels.com/api/
2. Sign up → copy API key into `.env` as `PEXELS_API_KEY`

### YouTube Data API v3 (OAuth)
1. Go to https://console.cloud.google.com/apis/library
2. Enable **YouTube Data API v3**
3. Go to **Credentials → Create → OAuth 2.0 Client ID**
4. Application type: **Desktop App**
5. Download JSON → save as `client_secret.json`
6. Run `python uploader/youtube.py` once to authorize in browser
7. This creates `token.json` (auto-refreshes forever after)

---

## ⚙️ Step 2: Local Setup

```bash
# Clone/enter project
cd shorts_bot

# Install system deps (Ubuntu/Debian)
sudo apt install ffmpeg imagemagick fonts-liberation -y

# Install Python deps
pip install -r requirements.txt

# Copy and fill in env file
cp .env.example .env
# Edit .env with your keys
```

---

## 🧪 Step 3: Test Each Component

```bash
# Test script generation only (no API cost)
python main.py test-script

# Test script + voice
python main.py test-voice

# Full pipeline, no upload (safe test)
python main.py dry-run

# Full pipeline + upload
python main.py run
```

---

## ☁️ Step 4: Deploy to GCP (run forever, free)

```bash
# Install gcloud CLI if needed
# https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Edit deploy_gcp.sh: set PROJECT_ID at the top
# Then run:
bash deploy_gcp.sh
```

This will:
- Build your Docker image
- Deploy as a Cloud Run Job
- Set up daily Cloud Scheduler at **09:00 UTC** (13:00 Dubai time)
- Store your secrets safely in Secret Manager

### Manual trigger anytime:
```bash
gcloud run jobs execute youtube-shorts-bot --region=us-central1
```

---

## 🎛️ Configuration Options

Edit `.env` to customize:

| Variable | Default | Description |
|---|---|---|
| `NICHE` | `AI and technology facts` | Content topic |
| `SHORTS_PER_DAY` | `1` | Videos per run |
| `VIDEO_DURATION_SEC` | `55` | Target length |
| `TTS_VOICE_NAME` | `en-US-Neural2-D` | Voice (see below) |
| `YT_PRIVACY` | `public` | public/private/unlisted |
| `BACKGROUND_MUSIC_PATH` | _(empty)_ | Path to royalty-free MP3 |

### Available Neural2 Voices
| Name | Style |
|---|---|
| `en-US-Neural2-D` | Male, authoritative |
| `en-US-Neural2-J` | Male, warm |
| `en-US-Neural2-F` | Female, clear |
| `en-US-Neural2-H` | Female, expressive |
| `en-GB-Neural2-B` | Male, British |

---

## 💡 Niche Ideas (proven performers)

```
AI and technology facts
mind-blowing science facts
psychology and human behavior
history facts most people don't know
space and universe facts
economics and money facts
```

Change via: `NICHE="psychology and human behavior"` in `.env`

---

## 📊 Free Tier Limits (you'll never hit these at 1/day)

| Service | Free Limit | Your Usage |
|---|---|---|
| Gemini 2.0 Flash | 1,500 req/day | 1/day |
| Google Cloud TTS | 1M chars/month | ~150/day |
| Pexels API | 200 req/hr | ~5/day |
| YouTube Upload | 10,000 units/day | ~1,600/upload |

---

## 🔧 Troubleshooting

**ImageMagick error with captions:**
```bash
sudo sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml
```

**YouTube quota exceeded:**
- Each upload uses ~1,600 of the 10,000 daily units
- You can post up to 6 shorts/day for free

**Whisper model slow first run:**
- Downloads ~150MB base model once, then cached forever

**GCP auth issues:**
```bash
gcloud auth application-default login
```
