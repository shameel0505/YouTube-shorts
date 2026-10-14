---
name: flow-character-director
description: Master orchestrator skill for autonomous character-consistent video production using Google Flow (gflow-cli, Veo 2, Imagen 3). Use this skill whenever generating multi-scene videos, YouTube Shorts, or stories featuring persistent characters with visual, vocal, and stylistic continuity.
---

# flow-character-director

This skill guides the autonomous creation of character-consistent video shorts using **Google Flow** (`gflow-cli`), **Veo 2** (T2V/R2V), **Imagen 3**, and this workspace's audio/subtitle stack.

## Core Principles

1. **Character Is the Only Persistent Identity in Flow**:
   Flow supports first-class `CHARACTER` entities (`gflow character create`). Locations, backgrounds, and props are image-level only (`--ref`).
2. **Deterministic `@Name` Reference Binding (MANDATORY AUTOMATION RULE)**:
   - On `flow.google.com`, character chips MUST be committed via keystrokes: `@` -> type character name letter-by-letter (`l-i-y-a`) -> wait for autocomplete popup -> press `Enter` -> append prompt text.
   - 🛑 **NEVER paste `@liya` as raw text** (`insert_text` or clipboard). Pasted text does NOT trigger the autocomplete popup and will fail to attach the character chip.
   - 🛑 **AGENTS MUST ASK THE USER BEFORE MODIFYING OR TOUCHING THIS CHARACTER FLOW.** See [AGENTS.md](file:///Users/shameel/Desktop/youtube/AGENTS.md) and [test_tag_liya.py](file:///Users/shameel/Desktop/youtube/scripts/test_tag_liya.py).
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
  "theme": "Kurzgesagt 2D Vector Graphic",
  "character": "Liya",
  "scenes": [
    {
      "scene_num": 1,
      "title": "Opening Hook",
      "type": "A-ROLL",
      "prompt": "[Scene 01 - Opening Hook]: Full-frame 9:16 image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens, medium waist-up shot at minimalist timber creator studio desk, host wearing the tailored matte charcoal overshirt over crisp crewneck with generous headroom, authentic natural skin texture with visible micro-pores, illuminated by warm 3200K softbox key light at 45 degrees with subtle warm rim accent, organic optical bokeh. The shot opens with the host looking directly into the camera lens with engaging warmth and closed mouth in a brief 0.5-second natural resting pause, takes a subtle breath, and then begins speaking with relaxed conviction saying: \"[Opening statement]\", using subtle natural hand gestures, and as the words finish, pauses naturally with a subtle knowing nod and rests hands easily on the timber desk, keeping warm direct eye contact with the viewer with zero frozen stillness or awkward sideways glances, sharp cinematic 4k.",
      "narration": "[Opening statement]",
      "duration": 6
    },
    {
      "scene_num": 2,
      "title": "Scientific Evidence Diagram",
      "type": "B-ROLL",
      "prompt": "[Scene 02 - Scientific Evidence Diagram]: Full-frame 9:16 image edge to edge, no bars. Prestigious educational scientific 2D vector animation in clean flat infographic style: deep matte navy-blue background (#0A1128). Crisp minimalist geometric icons: [mechanism]. Bold graphic silhouettes, smooth 2D mechanical motion, razor-sharp vector lines, high visual hierarchy, flat solid colors with luminous high-contrast accents, zero photorealism, zero 3D CGI reflections, off-screen narrator voiceover saying: \"[Voiceover line]\"",
      "narration": "[Voiceover line]",
      "previous_video": "Scene 01 - Opening Hook",
      "duration": 6
    }
  ]
}
```

Rules for high retention & structural integrity:
- **Unified B-Roll Theme**: ONE VIDEO = ONE UNIFIED B-ROLL THEME. All B-roll cutaways share the exact same visual identity (e.g. Kurzgesagt 2D Vector Graphic standard for science explainers).
- **Unique Slugging**: Every scene prompt starts with `[Scene {scene_num:02d} - {title}]: ` to guarantee unique, searchable Flow asset titles.
- **Continuation Chaining**: Every scene from Scene 2 onwards chains to its predecessor via `--previous-video`.
- **Speech Budget**: Spoken lines strictly between 10–14 words (<= 1.8 words/sec), 100% complete sentences with zero trailing fragments.
- **Aspect Ratio**: Always vertical `9:16`.

### Step 3: Scene Generation with Flow & Veo
Run the verified pipeline runner:
```bash
python experiments/autonomous_character_pipeline.py \
  --character liya \
  --scenes 10 \
  --aspect 9:16 \
  --profile youtube
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
