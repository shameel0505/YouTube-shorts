# YouTube Shorts Bot

A fully automated YouTube Shorts bot that researchers trending topics, writes a script using Gemini 2.0 Flash, generates voiceover audio using Google Cloud TTS, fetches background videos via Pexels, transcribes to add word-level captions, creates a polished vertical video, and uploads it as a Short to your YouTube channel. 

**Cost: $0/month** by using free tiers and open-source tools!

```text
+----------+      +-----------+     +------------+     +-------------+
| Research | ---> |  Script   | --> | Voiceover  | --> |  Footage    |
| (Reddit, |      | (Gemini)  |     | (GCP TTS)  |     |  (Pexels)   |
| Trends)  |      +-----------+     +------------+     +-------------+
+----------+                                                  |
                                                              v
+----------+      +-----------+     +------------+     +-------------+
| YouTube  | <--- | Assembly  | <-- |  Captions  | <-- | Transcription
|  Upload  |      | (MoviePy) |     |   (SRT)    |     |  (Whisper)  |
+----------+      +-----------+     +------------+     +-------------+
```

## Cost Breakdown (All Free)

| Service | Purpose | Free Tier Quota | Usage Per Video |
|---------|---------|-----------------|-----------------|
| Gemini API | Script generation | 1,500 req / day | ~2 requests |
| GCP Text-to-Speech | Voiceover (Neural2) | 1,000,000 chars / mo | ~750 chars |
| Pexels API | Background footage | 200 req / hour | ~5 requests |
| YouTube Data API v3 | Uploading short | 10,000 units / day | ~1,600 units |
| Faster Whisper | Transcription | Local | 0 |
| MoviePy | Video editing | Local | 0 |

## Prerequisites
- Python 3.11+
- System packages: `ffmpeg` and `imagemagick`

## API Setup
1. **Gemini API Key:** Get your free key from [Google AI Studio](https://aistudio.google.com/apikey).
2. **Google Cloud TTS:** Create a GCP project, enable `Cloud Text-to-Speech API`, create a Service Account with the `Cloud Text-to-Speech User` role, and download the JSON key.
3. **Pexels API Key:** Sign up for a free key at [Pexels API](https://www.pexels.com/api/).
4. **YouTube OAuth:** Go to GCP Console -> APIs & Services -> Credentials. Create an OAuth 2.0 Client ID for a "Desktop App". Download the JSON as `client_secret.json` and place it in the project root. On your first run, a browser window will open to authenticate your account and will generate `token.json` for future headless access.

## Local Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your keys and settings:
   ```bash
   cp .env.example .env
   ```
3. Run the OAuth authentication manually once:
   ```bash
   python main.py run
   ```

## Test Commands
Test the pipeline in stages without wasting quotas:
- `python main.py test-script` - Tests topic research and script generation.
- `python main.py test-voice` - Generates script and tests voiceover synthesis.
- `python main.py dry-run` - Runs the entire pipeline but skips YouTube upload.
- `python main.py run` - Full pipeline: generate and upload.
- `python main.py schedule` - Start a local APScheduler instance.

## GCP Deployment
You can deploy this as a daily serverless Cloud Run Job!
1. Open `deploy_gcp.sh` and edit the `PROJECT_ID` variable.
2. Ensure you have `client_secret.json` and `token.json` in your local directory (they are pushed as secrets).
3. Run the script:
   ```bash
   ./deploy_gcp.sh
   ```

## Configuration Reference
All of these variables can be set in `.env`:
| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Your Gemini 2.0 API key |
| `GCP_PROJECT_ID` | - | Your GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | `./service-account.json` | Path to your GCP service account JSON key |
| `YOUTUBE_CLIENT_SECRET_JSON` | `./client_secret.json` | Path to YouTube OAuth client secret |
| `PEXELS_API_KEY` | - | Pexels authorization key |
| `NICHE` | `AI and technology facts` | The overarching topic for your videos |
| `SHORTS_PER_DAY` | `1` | (Not utilized heavily by script yet) |
| `VIDEO_DURATION_SEC` | `55` | Target length of script and video |
| `TTS_VOICE_NAME` | `en-US-Neural2-D` | The voice to use. Female option: `en-US-Neural2-F` |
| `YT_PRIVACY` | `public` | `public`, `private`, or `unlisted` |

## Niche Ideas
Not sure what to post? Try these proven performers:
- AI and Machine Learning innovations
- Space and Astronomy facts
- Historical mysteries and events
- Personal finance and economics
- Psychology and human behavior tricks
- Futuristic technology concepts

## Troubleshooting
- **ImageMagick Policy Error:** If MoviePy fails to generate text clips on Linux, edit `/etc/ImageMagick-6/policy.xml` and change the line containing `pattern="@*"` from `rights="none"` to `rights="read|write"`.
- **YouTube Quota:** If you get quota errors, ensure you are uploading fewer than ~6 videos per day per GCP project.
- **Whisper Download:** The first time the script runs, it downloads a ~150MB model. Subsequent runs are cached. If deploying via Docker, the `Dockerfile` pre-downloads it for you!
