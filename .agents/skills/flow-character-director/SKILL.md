---
name: flow-character-director
description: Master orchestrator skill for autonomous character-consistent video production using Google Flow (gflow-cli, Veo 2, Imagen 3). Use this skill whenever generating multi-scene videos, YouTube Shorts, or stories featuring persistent characters with visual, vocal, and stylistic continuity.
---

# flow-character-director

This skill guides the autonomous creation of character-consistent video shorts using **Google Flow** (`gflow-cli`), **Veo 2** (T2V/R2V), **Imagen 3**, and this workspace's audio/subtitle stack.

## Core Principles

1. **Character Is the Only Persistent Identity in Flow**:
   Flow supports first-class `CHARACTER` entities (`gflow character create`). Locations, backgrounds, and props are image-level only (`--ref`).
2. **Deterministic `@Name` Reference Binding**:
   When generating scenes via `video t2v` or `video r2v`, tagging `@CharacterName` in the prompt automatically binds the character's facial and bodily reference images to the generation wire (`referenceEntities`).
3. **Pacing for Vertical Shorts (9:16)**:
   - Target duration: ~50–60 seconds total.
   - Pacing: 10 to 12 scenes, each 4 to 5 seconds long.
   - Visual change every 4–5 seconds prevents viewer drop-off.
4. **Quality Gates Over Impressions**:
   Every rendered clip must pass automated QA (`clip_qa.py`) to verify speech onset, face motion fluidity, and A/V sync before final delivery.

---

## The Autonomous Production Lifecycle

```
[1. Character Selection/Minting]
         │
         ▼
[2. Gemini Scriptwriting & Choreography]  <--- Embeds @CharacterName & camera motions
         │
         ▼
[3. Batch Veo Generation with WAF Protection]  <--- Retries on 403, applies exponential backoff
         │
         ▼
[4. Audio Harmonization & Whisper Subtitling]  <--- Voiceover, BGM, SFX triggers, ASS captions
         │
         ▼
[5. Automated QA & Verification Gate]  <--- clip_qa.py checks fluidity & sync
         │
         ▼
[6. Final Deliverable Export]  <--- Saved to output/experiments/autonomous_characters/final/
```

---

## Step-by-Step Runbook

### Step 1: Character Resolution
Check if the requested character exists in the target Flow project:
```bash
gflow character list --project <FLOW_PROJECT_ID>
```
If the character does not exist, mint them using `gflow character create`:
```bash
gflow character create \
  --project <FLOW_PROJECT_ID> \
  --name "Kaelen" \
  --face-prompt "A sharp-eyed 30-year-old male investigator with silver cybernetic temple implants, weathered features, neutral studio lighting, 8k portrait." \
  --body-prompt "Wearing a dark matte-leather duster coat with high collar, dark cargo trousers, combat boots, neutral lighting, full body turnaround." \
  --voice "Algenib" \
  --personality "Observant, cynical, calm under pressure, gravelly delivery."
```
> Note: Minting a character costs 2 image generations (covered by the free daily quota).

### Step 2: Scriptwriting with Gemini
Generate exactly 10 to 12 scenes with the following strict JSON schema:
```json
{
  "title": "Short Title",
  "character": "Kaelen",
  "scenes": [
    {
      "scene_num": 1,
      "prompt": "@Kaelen stands at the edge of a rain-swept neon rooftop looking down at a cyberpunk metropolis, slow cinematic drone orbit, 8k photorealistic, IMAX 70mm.",
      "narration": "They told us the machine was infallible... until it predicted its own destruction.",
      "duration": 5
    }
  ]
}
```

Rules for high retention:
- **Hook (0-3s)**: High curiosity or visual impact. No "Did you know".
- **Camera Grammar**: Explicit motion verb in every prompt (`slow push-in`, `drone orbit`, `macro tracking`, `low-angle pan`).
- **Aspect Ratio**: Always vertical `9:16`.

### Step 3: Batch Video Generation (Veo)
Run `gflow video t2v` for each scene:
```bash
gflow video t2v \
  "@Kaelen stands at the edge of a rain-swept neon rooftop..." \
  --project <FLOW_PROJECT_ID> \
  --aspect 9:16 \
  --profile youtube \
  --out-dir ./output/experiments/autonomous_characters/clips/ \
  --json
```

**Guardrails**:
- Set `GFLOW_CLI_HEADLESS=0` to avoid automated bot-detection.
- If HTTP 403 is received, pause for 30s and retry up to 3 attempts.
- Do not run concurrent generation on the same auth profile.

### Step 4: Audio, SFX & Subtitles
1. **Narration**: Concatenate spoken lines and synthesize master voiceover using `generator/voiceover.py` or native Flow audio.
2. **Audio Mixing**: Use `video/audio_mixer.py` to duck background music under the voiceover and trigger SFX risers at cut boundaries.
3. **Transcription & Dynamic Subtitles**: Run `video/captions.py` (Whisper) to generate word-level timestamps and burn styled subtitles with ASS/FFmpeg.

### Step 5: Quality Assurance
Run `clip_qa.py` on the assembled cut:
```bash
python .agents/skills/video-production/clip_qa.py ./output/experiments/autonomous_characters/final/output.mp4
```
- Verify `face_motion_p10 > 0.15` (no frozen face).
- Verify `sync_lag_s` within -0.045s to +0.125s (lip sync).

---

## Command Reference Quick Guide
- List voices: `gflow character voices`
- Check credits: `gflow credits user --profile youtube`
- List characters: `gflow character list --project <id>`
- Dry-run test: `python experiments/autonomous_character_pipeline.py --dry-run`
