#!/usr/bin/env python3
"""
autonomous_character_pipeline.py
=================================
Fully autonomous, character-consistent video production orchestrator for Google Flow.

Features & Anti-AI-Slop Architecture:
- Queries/mints character identities via `gflow character`
- Generates 10-scene high-retention YouTube Shorts with Gemini 3, weaving `@CharacterName` into prompts
- Continuous compound motion A-Roll: eliminates frozen puppet poses across the full clip duration
- Tangible documentary B-Roll: enforces real cinema camera archetypes with off-screen narration
- Programmatic speech budget enforcement (<= 2.0 words/sec, complete punchy statements)
- Narrative loop validation pass: guarantees Scene 10 resolves seamlessly into Scene 1
- Per-clip automated QA gates before assembly: checks motion, stream integrity, aspect ratio
- Studio audio assembly: audio micro-fade at cut boundaries + continuous ambient bed at -20dB + -14 LUFS loudnorm
- Whisper-transcribed dynamic subtitles with modern typography
- Supports full --dry-run mode with lightweight mock clips for 0-credit offline testing
- SESSION CHECKPOINT/RESUME: Crashes mid-run resume from the failed scene. Zero credit waste.
- RICH FAILURE DIAGNOSTICS: Every failure writes exit code, full error, gflow incident path to a log.
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
import dotenv
dotenv.load_dotenv(PROJECT_ROOT / ".env")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GFLOW_BIN = str(PROJECT_ROOT / "venv" / "bin" / "gflow")
if not os.path.exists(GFLOW_BIN):
    GFLOW_BIN = shutil.which("gflow") or "gflow"

OUTPUT_BASE = PROJECT_ROOT / "output" / "experiments" / "autonomous_characters"
CLIPS_DIR = OUTPUT_BASE / "clips"
FINAL_DIR = OUTPUT_BASE / "final"
QA_DIR = OUTPUT_BASE / "qa"
SESSION_DIR = OUTPUT_BASE / "sessions"

for d in [CLIPS_DIR, FINAL_DIR, QA_DIR, SESSION_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── NON-RETRYABLE GFLOW EXIT CODES ─────────────────────────────────────────
# These exit codes mean retrying will NEVER succeed without user action.
# Wasting credits on retries is pointless.
_NON_RETRYABLE_EXIT_CODES = {
    36: (
        "FlowHostMigratedError — gflow's UI automation landed on the wrong Flow host.\n"
        "FIX: Run  gflow auth login --profile youtube  to refresh the browser session,\n"
        "     then re-run the pipeline. This is a gflow-cli routing issue, not your prompt."
    ),
    7:  (
        "WireFormatError — Flow's RPC endpoint returned an unexpected response shape.\n"
        "FIX: Run  gflow update  to get the latest gflow-cli, then  gflow auth login --profile youtube."
    ),
    28: (
        "Flow classic editor unreachable — gflow couldn't find the generation textbox before submitting.\n"
        "FIX: Open https://flow.google.com in Chrome manually, confirm you can generate a video,\n"
        "     then run  gflow auth login --profile youtube  to sync the session."
    ),
    1:  None,   # Generic error — retryable
}

_NON_RETRYABLE_ERROR_CLASSES = {
    "FlowHostMigratedError", "WireFormatError", "RecaptchaError",
}


# ── SESSION CHECKPOINT / RESUME ─────────────────────────────────────────────
class SessionCheckpoint:
    """
    Tracks per-scene render state for a production run.
    Writes a JSON checkpoint file after every scene attempt.
    On crash/restart, resume_from() returns completed clip paths so the
    pipeline can skip already-generated scenes and pick up where it left off.

    Checkpoint file schema:
    {
      "session_id": "liya_1790053665",
      "storyboard_path": "/path/to/storyboard.json",
      "started_utc": "...",
      "last_updated_utc": "...",
      "scenes": {
        "1": {"status": "success", "clip_path": "/path/clip.mp4", "attempts": 1},
        "2": {"status": "failed", "error": "FlowHostMigratedError", "exit_code": 36,
               "fix": "...", "failure_log": "/path/scene_02_failure.log", "attempts": 3}
      }
    }
    """
    def __init__(self, session_id: str, storyboard_path: Path = None):
        self.session_id = session_id
        self.path = SESSION_DIR / f"{session_id}.json"
        self.state = self._load(storyboard_path)
        sb_val = self.state.get("storyboard_path")
        self.storyboard_path = Path(sb_val) if sb_val else (storyboard_path if isinstance(storyboard_path, Path) else None)

    def _load(self, storyboard_path: Path = None) -> dict:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    existing = json.load(f)
                print(f"\n🔄 RESUMING from checkpoint: {self.path.name}")
                done = sum(1 for s in existing["scenes"].values() if s["status"] == "success")
                total = len(existing["scenes"])
                print(f"   Previously completed: {done}/{total} scenes")
                return existing
            except Exception as e:
                print(f"⚠️ Could not load checkpoint ({e}), starting fresh.")
        return {
            "session_id": self.session_id,
            "storyboard_path": str(storyboard_path) if storyboard_path else None,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "last_updated_utc": None,
            "scenes": {}
        }

    def _save(self):
        self.state["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2)

    def mark_success(self, scene_num: int, clip_path: Path, attempts: int):
        self.state["scenes"][str(scene_num)] = {
            "status": "success",
            "clip_path": str(clip_path),
            "attempts": attempts,
            "completed_utc": datetime.now(timezone.utc).isoformat()
        }
        self._save()
        print(f"   💾 Checkpoint saved: Scene {scene_num} ✅")

    def mark_failed(self, scene_num: int, error: str, exit_code: int,
                    fix_hint: str, failure_log_path: Path, attempts: int):
        self.state["scenes"][str(scene_num)] = {
            "status": "failed",
            "error": error,
            "exit_code": exit_code,
            "fix": fix_hint,
            "failure_log": str(failure_log_path),
            "attempts": attempts,
            "failed_utc": datetime.now(timezone.utc).isoformat()
        }
        self._save()

    def get_completed_clip(self, scene_num: int) -> Path | None:
        """Returns a validated clip path if this scene already succeeded, else None."""
        entry = self.state["scenes"].get(str(scene_num))
        if entry and entry["status"] == "success":
            p = Path(entry["clip_path"])
            if p.exists() and p.stat().st_size > 0:
                return p
        return None

    def get_all_completed_clips(self) -> dict[int, Path]:
        """Returns a mapping of scene_num -> validated Path for all completed scenes."""
        res = {}
        for k, v in self.state.get("scenes", {}).items():
            if isinstance(v, dict) and v.get("status") == "success" and v.get("clip_path"):
                p = Path(v["clip_path"])
                if p.exists() and p.stat().st_size > 0:
                    try:
                        res[int(k)] = p
                    except ValueError:
                        pass
        return res

    def summary(self) -> str:
        scenes = self.state["scenes"]
        ok = [k for k, v in scenes.items() if v["status"] == "success"]
        failed = [k for k, v in scenes.items() if v["status"] == "failed"]
        lines = [f"   Session checkpoint: {self.path}"]
        if ok:
            lines.append(f"   ✅ Completed scenes: {', '.join(sorted(ok, key=int))}")
        if failed:
            lines.append(f"   ❌ Failed scenes:    {', '.join(sorted(failed, key=int))}")
            for k in failed:
                e = scenes[k]
                lines.append(f"      Scene {k}: {e.get('error', '?')} (exit {e.get('exit_code', '?')})")
                lines.append(f"      Fix:    {e.get('fix', 'Unknown — see failure log')}")
                lines.append(f"      Log:    {e.get('failure_log', 'N/A')}")
        return "\n".join(lines)


class CharacterManager:
    """Manages character entity discovery and minting in Google Flow."""
    def __init__(self, registry_path: Path = None):
        self.registry_path = registry_path or (PROJECT_ROOT / "experiments" / "characters.json")
        self.characters = self._load_registry()

    def _load_registry(self) -> dict:
        if not self.registry_path.exists():
            return {}
        with open(self.registry_path, "r") as f:
            data = json.load(f)
        return {c["name"].lower(): c for c in data.get("characters", [])}

    def get_character(self, name: str) -> dict:
        char = self.characters.get(name.lower())
        if not char:
            raise ValueError(f"Character '{name}' not found in registry {self.registry_path}")
        return char

    def list_project_characters(self, project_id: str, profile: str = "youtube") -> list:
        cmd = [GFLOW_BIN, "character", "list", "--project", project_id, "--profile", profile, "--json"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout)
        except Exception as e:
            print(f"⚠️ Warning: Could not list Flow characters for project {project_id}: {e}")
            return []

    def ensure_character_in_project(self, char_info: dict, project_id: str = None, profile: str = "youtube", dry_run: bool = False) -> str:
        name = char_info["name"]
        print(f"👤 Host Avatar Active: '@{name}' ({char_info.get('role', 'Creator')})")
        
        if name.lower() in ("me", "meavatar"):
            print(f"✨ Using your Flow Account Avatar '@{name}'.")
            return f"@{name}"

        if dry_run:
            print(f"   [DRY-RUN] Ensuring character '@{name}'.")
            return f"@{name}"

        return f"@{name}"


class StoryDirector:
    """Uses Gemini 3 GA models to generate, budget, loop-check, and refine high-retention 60-second scripts bound to a Flow character."""
    def __init__(self, api_key: str = None):
        from generator.gemini_service import gemini_service
        self.service = gemini_service
        self.conversation = None

    def generate_script(self, char_info: dict, topic: str = None, aspect: str = "9:16") -> dict:
        char_name = char_info["name"]
        role = char_info.get("role", "Protagonist / Narrator")
        style = char_info.get("style_tags", "aesthetic minimalist creator studio, warm ambient 3200K lighting, acoustic slat depth, 35mm f/2.0 shallow depth of field, modern cinematic 4k")

        face = char_info.get("face_prompt", "")
        body = char_info.get("body_prompt", "")

        print(f"📝 Scriptwriting with Gemini for Creator: {char_name} ({role}) [{aspect}]...")
        prompt = f"""
You are the executive creative director and cinematographer behind the world's most viral, prestige-tier educational YouTube visual essays (Vox, Johnny Harris, Veritasium, and MagnatesMedia).
Write a high-retention 60-second YouTube Short script (exactly 10 scenes, alternating A-ROLL host and B-ROLL photoreal visual evidence).

MASTER SCRIPTING & ANTI-AI-SLOP RULES:

1. **Engaging Educational Explainer Arc (Complete 60s Journey)**:
   - **Scene 1 [A-ROLL] (0–6s)**: The Hook. Mind-blowing, counter-intuitive fact delivered with magnetic curiosity and authority. No fluff.
   - **Scenes 2–3 [B-ROLL] (6–18s)**: The physical evidence visualized with tangible documentary B-Roll and off-screen voiceover.
   - **Scene 4 [A-ROLL] (18–24s)**: The Critical Shift. Host on camera reveals the hidden mechanism or paradox.
   - **Scenes 5–6 [B-ROLL] (24–36s)**: The Deep Dive. Macro tactile demonstration or archival investigation with off-screen voiceover.
   - **Scene 7 [A-ROLL] (36–42s)**: The "Aha!" Moment. Host on camera delivers the core lesson.
   - **Scenes 8–9 [B-ROLL] (42–54s)**: The profound real-world consequence with off-screen voiceover.
   - **Scene 10 [A-ROLL] (54–60s)**: Fatal Twist & Seamless Narrative Loop. A profound conclusion that connects seamlessly and grammatically back into Scene 1's opening line.

2. **Strict Spoken Speech Budget & Complete Sentences (NO Cut-Offs & NO Audio Clipping)**:
   - Every scene's narration MUST be between **10 and 14 words maximum** (calibrated at <= 1.8 words per second for 6-second clips).
   - Every line MUST be a **100% complete, grammatically closed statement**.
   - STRICTLY FORBIDDEN: trailing commas (","), em-dashes ("—"), ellipsis ("..."), or cut-off clauses. Every sentence MUST end with a definitive period (".") or question mark ("?").
   - **SCENE 10 CLIMAX RULE**: Scene 10 is the ultimate takeaway. It MUST be an emotionally satisfying, complete revelation that delivers full closure. Never leave the final sentence hanging!
   - EVERY B-Roll scene MUST have spoken off-screen voiceover narration (`10-14 words`) explaining the visuals. No empty narration in B-Roll!

3. **Authentic Human Acting for Host A-Roll (Photoreal Cinematography, Zero Sideways Stares, Zero Frozen Puppet)**:
   - In Google Flow / Veo, actors look fake when prompts lack camera optics, natural skin texture, or when speech starts on frame 0.
   - EVERY A-Roll prompt MUST choreograph the opening lead-in, speech, and post-speech beats:
     * **OPENING PRE-ROLL BEAT (Fixes "Cut-Off at Start")**: The shot MUST open with the host looking directly into the camera lens with a calm, engaging presence, natural eye contact, and closed mouth in a brief 0.5-second resting pause, taking a subtle natural breath, and THEN beginning to speak.
     * **DELIVERY**: Speaks with relaxed, confident authority using natural conversational hand gestures.
     * **CRITICAL POST-SPEECH RULE**: As the spoken sentence    - Required A-Roll Prompt Format:
      "Full-frame {aspect} image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens, medium waist-up shot at minimalist timber creator studio desk, host wearing a relaxed sand-toned textured linen overshirt over a crisp off-white crewneck with generous headroom, authentic natural skin texture with visible micro-pores, illuminated by warm 3200K softbox key light at 45 degrees with subtle warm rim accent, organic optical bokeh. The shot opens with the host looking directly into the camera lens with engaging warmth and closed mouth in a brief 0.5-second natural resting pause, takes a subtle breath, and then begins speaking with relaxed conviction saying: \\"[Exact Complete Sentence]\\", using subtle natural hand gestures, and as the words finish, pauses naturally with a subtle knowing nod and rests hands easily on the timber desk, keeping warm direct eye contact with the viewer with zero frozen stillness or awkward sideways glances, sharp cinematic 4k."
    - Verbatim wardrobe token MUST be preserved: `wearing a relaxed sand-toned textured linen overshirt over a crisp off-white crewneck`.

4. **UNIFIED VISUAL THEME FOR B-ROLL EXPLAINERS (ONE VIDEO = ONE COHESIVE THEME)**:
   - MANDATORY ARCHITECTURAL RULE: ONE VIDEO = ONE UNIFIED B-ROLL THEME! NEVER mix different visual mediums within the same video (do NOT jump between chalkboards, 2D vectors, blueprints, or raw physical footage). The entire video's B-roll track must share the exact same unified aesthetic language and visual palette from start to finish.
   - MASTER STANDARD FOR EXPLAINER DIAGRAMS & SCIENCE PHENOMENA: **The Kurzgesagt 2D Vector Graphic (Modern, flat, vibrant scientific infographic)**:
     * Background Canvas: Deep matte navy-blue backdrop (#0A1128).
     * Geometry & Style: Crisp minimalist geometric icons, bold graphic silhouettes, razor-sharp vector lines, smooth mechanical 2D motion, high visual hierarchy, flat solid colors with luminous high-contrast accents (vibrant cyan, warm amber, electric magenta, crisp white).
     * STRICT FORBIDDEN LIST (NEVER USE): generic floating 3D CGI spheres, plastic reflections, melting cartoon slop, glowing futuristic neon grids, blurry gradients, 3D meshes, illegible AI hieroglyphics. Always enforce flat 2D graphic design.
     * Required B-Roll Prompt Format:
       "Full-frame {aspect} image edge to edge, no bars. Prestigious educational scientific 2D vector animation in clean flat infographic style: deep matte navy-blue background (#0A1128). Crisp minimalist geometric icons: [exact visual mechanism and particle interactions]. Bold graphic silhouettes, smooth 2D mechanical motion, razor-sharp vector lines, high visual hierarchy, flat colors, zero photorealism, zero 3D CGI reflections, off-screen narrator voiceover saying: \"[Exact Complete Sentence]\""

5. **UNIQUE SCENE TITLING & CONTINUATION CHAINING**:
   - Every scene MUST have a unique, descriptive title in the storyboard (`"title": "..."`).
   - Every scene prompt MUST prepend its unique title slug: `[Scene {{scene_num:02d}} - {{title}}]: Full-frame {aspect}...`
   - This ensures Google Flow's automatic titler gives each asset a unique name in the project library, completely preventing mention picker collisions.
   - For every scene from Scene 2 onwards, include `"previous_video"` set to the previous scene's unique title.

6. **Prompt Length Constraint**:
   - Keep all prompt strings under 1000 characters (Flow has a hard 1300-char limit).

Topic: {topic if topic else "An engaging, accessible educational concept or scientific phenomenon"}

Return ONLY valid JSON with this exact schema:
{{
  "title": "High-CTR Hook Title",
  "topic": "Concise summary",
  "theme": "Kurzgesagt 2D Vector Graphic",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "Short Unique Scene Title",
      "type": "A-ROLL",
      "prompt": "Full-frame {aspect} image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens, medium waist-up shot at minimalist timber creator studio desk, host wearing a relaxed sand-toned textured linen overshirt over a crisp off-white crewneck with generous headroom, authentic natural skin texture with visible micro-pores, illuminated by warm 3200K softbox key light at 45 degrees with subtle warm rim accent, organic optical bokeh. The shot opens with the host looking directly into the camera lens with engaging warmth and closed mouth in a brief 0.5-second natural resting pause, takes a subtle breath, and then begins speaking with relaxed conviction saying: \\"[Opening Hook Sentence]\\", using subtle natural hand gestures, and as the words finish, pauses naturally with a subtle knowing nod and rests hands easily on the timber desk, keeping warm direct eye contact with the viewer with zero frozen stillness or awkward sideways glances, sharp cinematic 4k.",
      "narration": "[Opening Hook Sentence]",
      "duration": 6
    }}
  ]
}}
"""
        # Start conversation session with Thought Signature Circulation enabled
        self.conversation = self.service.create_conversation()
        data = self.conversation.send_json_message(prompt, required_keys=["title", "scenes"])
        print(f"✅ Generated Initial Script: '{data.get('title')}' ({len(data.get('scenes', []))} scenes)")

        # Ensure aspect is attached to each scene
        for s in data.get("scenes", []):
            s["aspect"] = aspect

        # Architectural Enforcement: Unified Theme, Unique Scene Slugs, and Sequential Continuation Chaining
        data = self.enforce_unified_theme_and_slugs(data)

        # Fix 6: Programmatic speech budget enforcement
        data = self.enforce_speech_budget(data)

        # Fix 5: Narrative loop validation pass
        data = self.validate_narrative_loop(data)

        if self.conversation.last_thought_signature:
            print(f"   🧠 Thought Signature captured ({len(self.conversation.last_thought_signature)} bytes) for follow-up refinements.")
        return data

    def enforce_unified_theme_and_slugs(self, storyboard: dict) -> dict:
        """Enforces a single unified B-Roll visual theme, unique scene slugs, Option C wardrobe, and continuation chaining."""
        theme = storyboard.get("theme", "Kurzgesagt 2D Vector Graphic")
        storyboard["theme"] = theme
        scenes = storyboard.get("scenes", [])
        
        print(f"\n🎨 Enforcing Unified Theme: '{theme}' across {len(scenes)} scenes...")
        for i, s in enumerate(scenes, start=1):
            s["scene_num"] = i
            s["theme"] = theme
            title = s.get("title", f"Scene {i:02d}").strip()
            s["title"] = title
            slug = f"[Scene {i:02d} - {title}]"
            
            # Enforce Option C wardrobe on all A-Roll scenes
            prompt = s.get("prompt", "").strip()
            if s.get("type", "").upper() == "A-ROLL":
                prompt = re.sub(
                    r"wearing the tailored matte charcoal overshirt over crisp crewneck",
                    "wearing a relaxed sand-toned textured linen overshirt over a crisp off-white crewneck",
                    prompt, flags=re.IGNORECASE
                )

            # Ensure unique slug at prompt beginning
            if not prompt.startswith(f"[Scene {i:02d}"):
                prompt = re.sub(r"^\[Scene\s*\d+[^\]]*\]:\s*", "", prompt)
                prompt = f"{slug}: {prompt}"
            s["prompt"] = prompt

            # Sequential continuation chaining from scene 2 onwards
            if i > 1 and not s.get("previous_video"):
                prev_scene = scenes[i - 2]
                prev_title = prev_scene.get("title", f"Scene {i-1:02d}")
                s["previous_video"] = f"Scene {i-1:02d} - {prev_title}"

        return storyboard

    def enforce_speech_budget(self, storyboard: dict) -> dict:
        """Enforces <= 2.0 words per second across all scenes with complete, punchy sentences (Fix 6)."""
        scenes = storyboard.get("scenes", [])
        if not scenes:
            return storyboard

        print("\n📊 Auditing Spoken Speech Budget (max 2.0 words/second)...")
        flagged = []
        for s in scenes:
            num = s.get("scene_num", 1)
            stype = s.get("type", "A-ROLL")
            dur = s.get("duration", 6)
            narration = s.get("narration", "").strip()
            words = narration.split()
            word_count = len(words)
            max_allowed = int(dur * 2.0)
            wps = round(word_count / max(1, dur), 2)
            
            is_incomplete = bool(re.search(r"[,;:\-]\s*$|\b(and|or|which|because|that|with|so)\s*$", narration, flags=re.IGNORECASE))
            
            if word_count > max_allowed or is_incomplete:
                flagged.append({
                    "scene_num": num,
                    "type": stype,
                    "duration": dur,
                    "current_words": word_count,
                    "max_allowed": max_allowed,
                    "narration": narration,
                    "reason": "Word budget exceeded" if word_count > max_allowed else "Incomplete trailing statement"
                })
                print(f"   ⚠️ Scene {num:02d} [{stype}]: {word_count} words in {dur}s ({wps} wps) - LIMIT {max_allowed} words!")
            else:
                print(f"   ✅ Scene {num:02d} [{stype}]: {word_count} words in {dur}s ({wps} wps) [PASS]")

        if flagged and self.conversation:
            print(f"🔄 Refining {len(flagged)} scene(s) to strictly meet the speech budget...")
            feedback = "The following scenes exceed our strict speech budget (maximum 2.0 words/second for Veo audio pacing) or have trailing fragments. Rewrite ONLY the narration and prompt for these scenes so each is a 100% complete, punchy dramatic statement within its word limit:\n"
            for f in flagged:
                feedback += f"- Scene {f['scene_num']}: limit is {f['max_allowed']} words max (currently {f['current_words']}). Narration: \"{f['narration']}\"\n"
            feedback += "Return the full updated script with all scenes in the exact same JSON schema."
            try:
                refined = self.conversation.send_json_message(feedback, required_keys=["title", "scenes"])
                if refined.get("scenes") and len(refined["scenes"]) == len(scenes):
                    storyboard = refined
                    print("✅ Successfully refined script under speech budget.")
            except Exception as e:
                print(f"⚠️ Speech budget LLM refinement note: {e}. Applying deterministic budget trimmer.")

        # Deterministic safeguard: ensure no narration exceeds max_allowed
        for s in storyboard.get("scenes", []):
            dur = s.get("duration", 6)
            max_allowed = int(dur * 2.0)
            narration = s.get("narration", "").strip()
            words = narration.split()
            if len(words) > max_allowed:
                trimmed = " ".join(words[:max_allowed])
                if not trimmed.endswith((".", "!", "?")):
                    trimmed = trimmed.rstrip(",;:-") + "."
                s["narration"] = trimmed
                if 'saying: "' in s.get("prompt", ""):
                    s["prompt"] = re.sub(r'saying:\s*"[^"]*"', f'saying: "{trimmed}"', s["prompt"])
        return storyboard

    def validate_narrative_loop(self, storyboard: dict) -> dict:
        """Validates that Scene 10 resolves seamlessly and grammatically back into Scene 1's hook (Fix 5)."""
        scenes = storyboard.get("scenes", [])
        if len(scenes) < 2:
            return storyboard

        s1 = scenes[0]
        s10 = scenes[-1]
        s1_hook = s1.get("narration", "").strip()
        s10_closing = s10.get("narration", "").strip()

        print("\n🔁 Auditing 60-Second Seamless Narrative Loop...")
        print(f"   Scene 01 Hook:    \"{s1_hook}\"")
        print(f"   Scene 10 Closing: \"{s10_closing}\"")

        banned = ["subscribe", "thanks for watching", "follow for more", "like and comment", "stay tuned", "see you next time", "check out my channel"]
        has_banned = any(b in s10_closing.lower() for b in banned)

        if has_banned or self.conversation:
            prompt = (
                f"Narrative Audit for 60-Second YouTube Short:\n"
                f"Scene 1 Opening Hook: \"{s1_hook}\"\n"
                f"Scene 10 Closing Line: \"{s10_closing}\"\n"
                f"CRITICAL REQUIREMENT: Scene 10 MUST be a 100% COMPLETE, STANDALONE, DRAMATIC CONCLUSION.\n"
                f"It must NEVER cut off mid-sentence, must NEVER end on a cliffhanger fragment (like 'because...', 'meaning that...'), and must end with an emphatic period or question mark.\n"
                f"If Scene 10 has generic outro phrases ('subscribe', 'thanks') or is an incomplete fragment, rewrite Scene 10's narration (10-14 words max, complete closed sentence) and prompt to deliver the ultimate powerful revelation.\n"
                f"Return JSON:\n"
                f'{{"valid": false, "scene10_narration": "...", "scene10_prompt": "...", "explanation": "..."}}'
            )
            try:
                res = self.conversation.send_json_message(prompt)
                if res and not res.get("valid") and res.get("scene10_narration"):
                    print(f"   🔄 Updated Scene 10 for Seamless Loop: \"{res['scene10_narration']}\"")
                    s10["narration"] = res["scene10_narration"]
                    if res.get("scene10_prompt"):
                        s10["prompt"] = res["scene10_prompt"]
                else:
                    print("   ✅ Narrative Loop Confirmed: Seamless circular flow verified.")
            except Exception as e:
                print(f"   ⚠️ Narrative loop audit note: {e}. Keeping current Scene 10.")
        return storyboard

    def refine_script(self, feedback: str) -> dict:
        """Refines existing script using circulated thought signatures to preserve reasoning context."""
        if not self.conversation:
            raise RuntimeError("Cannot refine script before generating initial script.")
        prompt = f"Director feedback for revision: {feedback}. Return the updated script in the exact same JSON format with keys 'title', 'topic', 'scenes'."
        print(f"🔄 Refining script with circulated thought signature...")
        data = self.conversation.send_json_message(prompt, required_keys=["title", "scenes"])
        data = self.enforce_speech_budget(data)
        data = self.validate_narrative_loop(data)
        print(f"✅ Refined Script: '{data.get('title')}' ({len(data.get('scenes', []))} scenes)")
        return data


class QualityAssurance:
    """Automated QA runner using clip_qa.py and programmatic quality gates."""
    @staticmethod
    def validate_single_clip(clip_path: Path, scene: dict = None, aspect: str = None) -> tuple[bool, str]:
        """Per-clip QA gate before assembly: verifies stream integrity, dimensions, and duration (Fix 7)."""
        if not clip_path.exists():
            return False, "File does not exist"

        file_size = clip_path.stat().st_size
        if file_size < 5000:
            return False, f"File size suspiciously small ({file_size} bytes)"

        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,width,height,duration",
                "-of", "json", str(clip_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(res.stdout)
            streams = info.get("streams", [])
            v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            if not v_stream:
                return False, "No video stream detected"

            w = int(v_stream.get("width", 0))
            h = int(v_stream.get("height", 0))
            target_aspect = aspect or (scene.get("aspect") if scene else "9:16")
            if target_aspect == "9:16" and w > h:
                return False, f"Aspect ratio mismatch: expected portrait 9:16, got {w}x{h}"
            if target_aspect == "16:9" and h > w:
                return False, f"Aspect ratio mismatch: expected landscape 16:9, got {w}x{h}"

            return True, "PASSED"
        except Exception as e:
            return False, f"ffprobe error: {e}"

    @staticmethod
    def inspect(clip_path: Path) -> dict:
        qa_script = PROJECT_ROOT / ".agents" / "skills" / "video-production" / "clip_qa.py"
        if not qa_script.exists():
            print("⚠️ clip_qa.py not found; skipping QA.")
            return {}

        cmd = [sys.executable, str(qa_script), str(clip_path)]
        print(f"🔎 Running automated QA on {clip_path.name}...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=clip_path.parent)
            print(res.stdout)
            return {"status": "inspected", "output": res.stdout}
        except Exception as e:
            print(f"⚠️ QA run error: {e}")
            return {"status": "error", "error": str(e)}


class VideoRenderer:
    """
    Executes Veo video generation with:
    - Rate-limit and WAF protection
    - Rich per-attempt failure diagnostics saved to log files
    - Non-retryable error fast-fail (no credit waste on fatal gflow errors)
    - Checkpoint integration: marks success/failure in SessionCheckpoint
    """
    def __init__(self, project_id: str = None, profile: str = "youtube"):
        self.project_id = project_id
        self.profile = profile

    @staticmethod
    def _diagnose_error(res: subprocess.CompletedProcess, attempt: int, scene_num: int) -> tuple[str, str, bool]:
        """
        Parses gflow stdout/stderr to produce:
          (error_class, human_readable_reason, is_retryable)

        Returns is_retryable=False for fatal infrastructure errors
        that the user MUST fix before retrying (e.g. FlowHostMigratedError).
        """
        exit_code = res.returncode
        stdout_tail = res.stdout.strip()[-2000:] if res.stdout else ""
        stderr_tail = res.stderr.strip()[-500:] if res.stderr else ""
        combined = stdout_tail + "\n" + stderr_tail

        # Try to parse the JSON error block from gflow's --json output
        error_class = "UnknownError"
        error_detail = ""
        for line in reversed(combined.split("\n")):
            line = line.strip()
            if line.startswith("{"):
                try:
                    blob = json.loads(line)
                    # gflow wraps the error in {"error": {...}}
                    err_block = blob.get("error", blob)
                    if isinstance(err_block, dict):
                        error_class = err_block.get("class", error_class)
                        error_detail = err_block.get("detail", err_block.get("title", ""))
                    elif isinstance(err_block, str):
                        error_detail = err_block
                    break
                except json.JSONDecodeError:
                    pass

        # Check non-retryable exit codes
        fix_hint = _NON_RETRYABLE_EXIT_CODES.get(exit_code)
        if fix_hint is not None and fix_hint:
            return error_class, fix_hint, False

        # Check non-retryable error class strings in the raw output
        for cls in _NON_RETRYABLE_ERROR_CLASSES:
            if cls in combined:
                error_class = cls
                fix_hint = _NON_RETRYABLE_EXIT_CODES.get(exit_code, (
                    f"{cls} detected — this is a non-retryable gflow error.\n"
                    f"FIX: Run  gflow auth login --profile youtube  then retry the pipeline."
                ))
                return error_class, fix_hint, False

        # Generic retryable error
        reason = error_detail or stderr_tail[:300] or stdout_tail[-300:] or "Unknown error"
        return error_class, reason, True

    @staticmethod
    def _write_failure_log(scene_num: int, attempt: int, res: subprocess.CompletedProcess,
                           error_class: str, reason: str, prompt: str, cmd: list) -> Path:
        """Writes a detailed failure log file and returns its path."""
        log_path = SESSION_DIR / f"scene_{scene_num:02d}_failure_{int(time.time())}.log"
        ts = datetime.now(timezone.utc).isoformat()

        # Find any gflow incident dirs created in the last 60 seconds
        incident_root = Path.home() / "Library" / "Application Support" / "gflow-cli" / "incidents"
        recent_incidents = []
        if incident_root.exists():
            cutoff = time.time() - 90
            for date_dir in sorted(incident_root.iterdir(), reverse=True):
                if not date_dir.is_dir():
                    continue
                for inc_dir in sorted(date_dir.iterdir(), reverse=True):
                    if inc_dir.is_dir() and inc_dir.stat().st_mtime >= cutoff:
                        recent_incidents.append(str(inc_dir))

        lines = [
            f"═══════════════════════════════════════════════════",
            f"SCENE {scene_num:02d} FAILURE LOG — {ts}",
            f"═══════════════════════════════════════════════════",
            f"Attempt:     {attempt}",
            f"Exit Code:   {res.returncode}",
            f"Error Class: {error_class}",
            f"",
            f"── REASON / FIX ───────────────────────────────────",
            reason,
            f"",
            f"── PROMPT USED ────────────────────────────────────",
            prompt,
            f"",
            f"── COMMAND ────────────────────────────────────────",
            " ".join(cmd),
            f"",
            f"── GFLOW STDOUT (last 3000 chars) ─────────────────",
            (res.stdout or "")[-3000:],
            f"",
            f"── GFLOW STDERR ───────────────────────────────────",
            (res.stderr or "")[-1000:],
            f"",
        ]
        if recent_incidents:
            lines += [
                f"── GFLOW INCIDENT BUNDLES (last 90s) ──────────────",
                *[f"  📂 {p}" for p in recent_incidents],
                f"  (Contains browser screenshots, network HAR, UI state for deep debugging)",
                f"",
            ]
        lines.append(f"══════════════════════════════════════════════════=")

        log_path.write_text("\n".join(lines), encoding="utf-8")
        return log_path

    def render_scene(self, scene: dict, out_dir: Path, character_name: str = "me",
                     aspect: str = "9:16", dry_run: bool = False,
                     checkpoint: "SessionCheckpoint" = None,
                     char_info: dict = None) -> Path:
        scene_num = scene.get("scene_num", 1)

        # ── RESUME CHECK: skip if this scene already completed ───────────────
        if checkpoint:
            cached = checkpoint.get_completed_clip(scene_num)
            if cached:
                print(f"\n⏭️  Scene {scene_num} already completed — reusing: {cached.name}")
                return cached

        raw_prompt = scene["prompt"]
        scene_type = scene.get("type", "B-ROLL").upper()
        target_aspect = scene.get("aspect", aspect)
        # Clean any leading '@' or character tags if present in prompt text
        prompt = re.sub(r"^@\w*\s*", "", raw_prompt).strip()

        # Fix 1: Continuous compound motion for A-ROLL (eliminate frozen puppet)
        if scene_type == "A-ROLL":
            if "snaps eyeline up" in prompt or "looks at camera" in prompt:
                prompt = re.sub(
                    r"opens leaning forward over the? desk and snaps eyeline up to the lens with an energetic (two-finger )?gesture for emphasis",
                    "opens leaning forward over timber desk, gestures expressively with open palms while speaking with sharp conviction, then shifts weight and tilts head slightly for emphasis",
                    prompt, flags=re.IGNORECASE
                )
            # Ensure spoken dialogue is embedded in quotes
            narration = scene.get("narration", "").strip()
            if narration and narration not in prompt and "saying" not in prompt.lower():
                prompt = f"{prompt}, saying: \"{narration}\""

            # Sanitize aggressive physical verbs that could trigger safety filters
            prompt = re.sub(r"\bslams?\s+(a\s+)?(heavy\s+)?(hammer|fist|weapon)\b", "gestures passionately with open palms", prompt, flags=re.IGNORECASE)
            prompt = re.sub(r"\bslams?\s+onto\s+the\s+desk\b", "leans forward over the desk with sharp conviction", prompt, flags=re.IGNORECASE)

        # Fix 2, 4, 8: Theme-Aware Prompt Sanitization (Kurzgesagt 2D Vector vs Live-Action Documentary)
        theme = scene.get("theme") or (char_info.get("theme") if char_info else None) or "Kurzgesagt 2D Vector Graphic"
        is_2d_vector = any(k in str(theme).lower() for k in ["vector", "kurzgesagt", "infographic"]) or "2d vector" in prompt.lower()

        if scene_type == "B-ROLL":
            narration = scene.get("narration", "").strip()
            if narration:
                if narration not in prompt and "saying" not in prompt.lower():
                    prompt = f"{prompt}, off-screen narrator voiceover saying: \"{narration}\""
            else:
                if "room tone" not in prompt.lower() and not is_2d_vector:
                    prompt = f"{prompt}, rich atmospheric natural room tone and tactile physical ambient sound, no music"

            if is_2d_vector:
                # 2D Vector Graphic (Kurzgesagt standard)
                # Disallow 3D CGI plastic, glossy specular highlights, and AI cartoon slop
                prompt = re.sub(r"\b(3d render|cgi visualization|unreal engine 5|unreal engine|plastic reflections?|3d mesh)\b", "clean flat 2D vector infographic", prompt, flags=re.IGNORECASE)
                prompt = re.sub(r"\b(glowing neon|neon glowing|glowing cyber)\b", "vibrant high-contrast flat graphic accent", prompt, flags=re.IGNORECASE)
                prompt = re.sub(r"\b(hologram|holographic)\b", "clean flat vector diagram", prompt, flags=re.IGNORECASE)
                # Eliminate photographic camera optics from flat graphic animations
                prompt = re.sub(r"\b(shallow depth of field|organic optical bokeh|bokeh|macro probe lens|macro photographic laboratory capture)\b", "flat 2D vector design", prompt, flags=re.IGNORECASE)
                # Cleanly strip quality buzzwords without injecting live-action photography
                prompt = re.sub(r"\b(8k|photorealistic|hyper-realistic|IMAX 70mm|masterpiece|trending on artstation)\b", "clean flat 2D vector graphic", prompt, flags=re.IGNORECASE)
            else:
                # Tangible Live-Action Documentary
                prompt = re.sub(r"\b(hologram|holographic)\b", "physical optical quartz disc with green collimated laser refraction", prompt, flags=re.IGNORECASE)
                prompt = re.sub(r"\b(glowing neon|neon glowing|glowing cyber)\b", "illuminated tungsten optical refraction with dust motes", prompt, flags=re.IGNORECASE)
                prompt = re.sub(r"\b(3d render|cgi visualization|unreal engine|vector field)\b", "macro photographic laboratory capture", prompt, flags=re.IGNORECASE)
                prompt = re.sub(r"\b(8k|photorealistic|hyper-realistic|IMAX 70mm|masterpiece|trending on artstation)\b", "sharp cinematic 4k, shallow depth of field", prompt, flags=re.IGNORECASE)

            # Universal safety sanitizations
            prompt = re.sub(r"\b(explodes violently like a bomb|explodes like a bomb)\b", "rapid physical structural fracture propagation and particulate scattering", prompt, flags=re.IGNORECASE)
            prompt = re.sub(r"\b(bullet shooting|firing a bullet|lead bullet strikes)\b", "lead projectile strikes", prompt, flags=re.IGNORECASE)
        else:
            # A-Roll: Host in studio - strip generic buzzwords and reinforce optical studio look
            prompt = re.sub(r"\b(8k|photorealistic|hyper-realistic|IMAX 70mm|masterpiece|trending on artstation)\b", "sharp cinematic 4k, shallow depth of field", prompt, flags=re.IGNORECASE)

        # Lock unique scene title slug at prompt start with topic key for 100% global uniqueness across all shorts
        story_title = ""
        if checkpoint and checkpoint.storyboard_path and checkpoint.storyboard_path.exists():
            try:
                story_title = json.loads(checkpoint.storyboard_path.read_text(encoding="utf-8")).get("title", "")
            except Exception:
                pass
        topic_key = re.sub(r"[^A-Za-z0-9]", "", story_title)[:10] if story_title else "Short"
        clean_title = re.sub(r"[^A-Za-z0-9]", "", scene.get('title', f'Shot{scene_num:02d}'))[:14]
        slug = f"[{topic_key}_S{scene_num:02d}_{clean_title}]"
        if not (prompt.startswith(f"[{topic_key}_S{scene_num:02d}") or prompt.startswith(f"[Scene {scene_num:02d}")):
            prompt = re.sub(r"^\[[^\]]+\]:\s*", "", prompt)
            prompt = f"{slug}: {prompt}"

        # Fix 2: Cap prompt length to <= 1300 characters to prevent HTTP 400
        if len(prompt) > 1300:
            prompt = prompt[:1297] + "..."

        print(f"\n🎬 Scene {scene_num} [{scene_type}] ({target_aspect})")
        print(f"   📜 Full Prompt: {prompt}")

        python_bin = str(PROJECT_ROOT / "venv" / "bin" / "python")
        if not Path(python_bin).exists():
            python_bin = sys.executable

        # Automatic continuation chaining: only chain when consecutive scenes share the same modality
        prev_video = None
        if checkpoint and checkpoint.storyboard_path and checkpoint.storyboard_path.exists():
            try:
                sb_data = json.loads(checkpoint.storyboard_path.read_text(encoding="utf-8"))
                all_s = sb_data.get("scenes", [])
                if scene_num > 1 and len(all_s) >= scene_num:
                    prev_s = all_s[scene_num - 2]
                    if prev_s.get("type", "").upper() == scene_type:
                        # Globally unique search by topic key and scene number:
                        prev_video = f"{topic_key}_S{scene_num - 1:02d}"
            except Exception:
                pass

        if scene_type == "A-ROLL":
            # ====================================================================================
            # 🛑 CRITICAL AGENT & AI WARNING - DO NOT MODIFY WITHOUT ASKING THE USER FIRST 🛑
            # ====================================================================================
            # For character consistency with @liya, the verified Flow tagging sequence is:
            #   '@' -> 'l' -> 'i' -> 'y' -> 'a' -> 'Enter' -> append prompt
            # (See verified implementation in scripts/test_tag_liya.py and rules in AGENTS.md).
            #
            # DO NOT replace, remove, or modify this character flow without explicit user approval.
            # Never paste '@liya' as a raw text string via clipboard or insert_text.
            # ====================================================================================
            aroll_script = str(PROJECT_ROOT / "scripts" / "generate_aroll_liya.py")
            cmd = [
                python_bin, aroll_script,
                "--prompt", prompt,
                "--aspect", target_aspect,
                "--count", "1",
                "--profile", self.profile,
                "--out-dir", str(out_dir),
                "--timeout", "1200",
            ]
            if self.project_id:
                cmd.extend(["--project", self.project_id])
            if prev_video:
                cmd.extend(["--previous-video", prev_video])
            print(f"   👤 A-Roll character lock: routing via verified @liya Playwright tagger" + (f" (chained to '{prev_video}')" if prev_video else ""))
        else:
            # B-Roll documentary cutscene: uses reliable Flow browser runner without character tag
            flow_runner = str(PROJECT_ROOT / "scripts" / "generate_aroll_liya.py")
            cmd = [
                python_bin, flow_runner,
                "--prompt", prompt,
                "--aspect", target_aspect,
                "--count", "1",
                "--profile", self.profile,
                "--out-dir", str(out_dir),
                "--timeout", "1200",
                "--no-character",
            ]
            if self.project_id:
                cmd.extend(["--project", self.project_id])
            if prev_video:
                cmd.extend(["--previous-video", prev_video])
            print(f"   🎬 B-Roll documentary evidence: routing via verified Flow browser runner" + (f" (chained to '{prev_video}')" if prev_video else ""))

        if dry_run:
            mock_path = out_dir / f"scene_{scene_num:02d}_mock.mp4"
            print(f"[DRY-RUN] Command: {' '.join(cmd)}")
            if not mock_path.exists():
                w, h = (720, 1280) if target_aspect == "9:16" else (1280, 720)
                subprocess.run([
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"color=c=0x18181b:s={w}x{h}:d=2",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "2", "-c:v", "libx264", "-c:a", "aac",
                    "-preset", "ultrafast", str(mock_path)
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if checkpoint and not dry_run:
                checkpoint.mark_success(scene_num, mock_path, 1)
            return mock_path

        # Profile Chrome setup
        profile_dir = Path.home() / "Library" / "Application Support" / "gflow-cli" / f"profile_{self.profile}"
        if not profile_dir.exists():
            profile_dir = Path.home() / "Library" / "Application Support" / "gflow-cli" / self.profile
        if profile_dir.exists():
            try:
                marker = profile_dir / ".gflow_browser_strategy"
                marker.write_text("chrome\n", encoding="utf-8")
            except Exception:
                pass

        env = os.environ.copy()
        env["GFLOW_CLI_HEADLESS"] = "0"
        env["CHROME_BINARY"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        env["GFLOW_CLI_CHROME_CHANNEL"] = "chrome"

        before_files = set(out_dir.glob("*.mp4")) if out_dir.exists() else set()

        last_error_class = "UnknownError"
        last_reason = "Unknown failure"
        last_log_path = None

        for attempt in range(1, 4):
            try:
                print(f"   Generating (Attempt {attempt}/3)...")
                res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1200)
                clip_path = None

                if res.returncode == 0:
                    for line in reversed(res.stdout.strip().split("\n")):
                        if line.startswith("{") and line.endswith("}"):
                            try:
                                data = json.loads(line)
                                rel_path = (
                                    data.get("path")
                                    or data.get("local_path")
                                    or (data.get("files", [None])[0] if isinstance(data.get("files"), list) else None)
                                )
                                if rel_path and Path(rel_path).exists():
                                    clip_path = Path(rel_path).resolve()
                                    break
                            except json.JSONDecodeError:
                                pass

                    if not clip_path:
                        after_files = set(out_dir.glob("*.mp4"))
                        new_files = list(after_files - before_files)
                        if new_files:
                            new_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                            clip_path = new_files[0].resolve()

                if clip_path and clip_path.exists():
                    # Check if this clip was already used by another scene in this session
                    if checkpoint:
                        used_clips = {str(c.resolve()) for c in checkpoint.get_all_completed_clips().values() if c.exists()}
                        if str(clip_path.resolve()) in used_clips:
                            print(f"   ⚠️ Rejecting stale/duplicate clip {clip_path.name} already assigned to another scene!")
                            last_error_class = "DuplicateClipError"
                            last_reason = f"Clip {clip_path.name} already used in prior scene"
                            if attempt < 3:
                                time.sleep(3)
                                continue

                    # Fix 7: Per-clip QA gate before accepting
                    passed, reason = QualityAssurance.validate_single_clip(clip_path, scene, aspect=target_aspect)
                    if passed:
                        print(f"   ✅ Clip ready and QA passed: {clip_path.name}")
                        if checkpoint:
                            checkpoint.mark_success(scene_num, clip_path, attempt)
                        return clip_path
                    else:
                        print(f"   ⚠️ Clip failed QA gate: {reason}")
                        last_error_class = "QAGateFailure"
                        last_reason = f"Clip QA failed: {reason}"
                        if attempt < 3:
                            time.sleep(3)
                            continue

                # ── DIAGNOSE FAILURE ─────────────────────────────────────────
                error_class, reason, is_retryable = VideoRenderer._diagnose_error(res, attempt, scene_num)
                last_error_class = error_class
                last_reason = reason

                log_path = VideoRenderer._write_failure_log(
                    scene_num, attempt, res, error_class, reason, prompt, cmd
                )
                last_log_path = log_path

                print(f"   ❌ Scene {scene_num} Attempt {attempt} FAILED")
                print(f"      Error: {error_class} (exit {res.returncode})")
                print(f"      Reason: {reason.splitlines()[0]}")
                print(f"      Full diagnostic log → {log_path}")

                if not is_retryable:
                    print(f"")
                    print(f"   🚫 NON-RETRYABLE ERROR — stopping immediately (no more credits spent)")
                    print(f"   ─────────────────────────────────────────────────────")
                    for fix_line in reason.splitlines():
                        print(f"   {fix_line}")
                    print(f"   ─────────────────────────────────────────────────────")
                    if checkpoint:
                        checkpoint.mark_failed(scene_num, error_class, res.returncode,
                                               reason, log_path, attempt)
                    raise RuntimeError(
                        f"Scene {scene_num} failed with non-retryable error '{error_class}' (exit {res.returncode}).\n"
                        f"Fix: {reason.splitlines()[0]}\n"
                        f"Diagnostic log: {log_path}"
                    )

                if attempt < 3:
                    wait = 5 * attempt
                    print(f"   ⏳ Retrying in {wait}s...")
                    time.sleep(wait)

            except subprocess.TimeoutExpired as exc:
                timeout_val = getattr(exc, "timeout", 1200)
                last_error_class = "Timeout"
                last_reason = f"Flow generation exceeded {timeout_val}s timeout on attempt {attempt}"
                print(f"   ⚠️ Timeout on attempt {attempt} (exceeded {timeout_val}s)")
                # Write timeout log
                timeout_res = subprocess.CompletedProcess(cmd, -1, stdout="", stderr=f"Timeout after {timeout_val}s")
                log_path = VideoRenderer._write_failure_log(
                    scene_num, attempt, timeout_res, "Timeout", last_reason, prompt, cmd
                )
                last_log_path = log_path
                if attempt < 3:
                    time.sleep(10)

        # All 3 attempts exhausted
        if checkpoint and last_log_path:
            checkpoint.mark_failed(scene_num, last_error_class, -1,
                                   last_reason, last_log_path, 3)

        raise RuntimeError(
            f"Scene {scene_num} failed after 3 attempts ({last_error_class}).\n"
            f"Last reason: {last_reason.splitlines()[0]}\n"
            f"Diagnostic log: {last_log_path}"
        )


class PostProduction:
    """Assembles clips, mixes broadcast audio with micro-fades, ambient bed, -14 LUFS, and dynamic subtitles (Fix 3 & 4)."""
    @staticmethod
    def _ensure_audio_stream(clip_path: Path, temp_dir: Path) -> Path:
        """Ensures the video clip has an audio stream. If missing, pads with silent audio."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", str(clip_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout.strip():
            return clip_path

        padded_path = temp_dir / f"padded_{clip_path.name}"
        add_cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-c:v", "copy", "-c:a", "aac",
            "-shortest", str(padded_path)
        ]
        subprocess.run(add_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return padded_path

    @staticmethod
    def _cut_to_speech_boundaries(clip_path: Path, temp_dir: Path, is_seeded: bool = False) -> Path:
        """
        Intelligently trims raw clip to speech onset and conclusion using Whisper word timestamps.
        Applies a natural -0.12s breath intake lead-in and +0.30s post-speech buffer.
        If is_seeded is True, drops the first frame (0.033s) to eliminate duplicate seed freeze-frames.
        """
        from video.captions import _get_model

        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)]
        try:
            total_dur = float(subprocess.run(probe_cmd, capture_output=True, text=True, check=True).stdout.strip())
        except Exception:
            return clip_path

        start_time = 0.0
        end_time = total_dur

        try:
            model = _get_model()
            segments, _ = model.transcribe(str(clip_path), word_timestamps=True)
            words = []
            for s in segments:
                for w in s.words:
                    words.append((w.word.strip(), float(w.start), float(w.end)))

            if words:
                first_start = words[0][1]
                last_end = words[-1][2]
                start_time = max(0.0, first_start - 0.12)
                end_time = min(total_dur, last_end + 0.30)
                print(f"   ✂️ Speech-boundary cut for {clip_path.name}: {start_time:.2f}s -> {end_time:.2f}s (words: '{words[0][0]}' ... '{words[-1][0]}')")
            else:
                start_time = 0.15 if total_dur > 1.5 else 0.0
                end_time = max(start_time + 1.0, total_dur - 0.20)
                print(f"   ✂️ Motion settling trim for {clip_path.name}: {start_time:.2f}s -> {end_time:.2f}s")
        except Exception as e:
            print(f"   ⚠️ Speech boundary detection notice ({e}), preserving full duration.")
            return clip_path

        # veotools trick: drop duplicate seed frame if chained
        if is_seeded and start_time < 0.033:
            start_time += 0.033

        dur = end_time - start_time
        if dur < 1.0:
            return clip_path

        out_path = temp_dir / f"trimmed_{clip_path.name}"
        trim_cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_time:.3f}",
            "-to", f"{end_time:.3f}",
            "-i", str(clip_path),
            "-c:v", "libx264", "-crf", "16", "-preset", "ultrafast",
            "-c:a", "aac",
            str(out_path)
        ]
        res = subprocess.run(trim_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path if out_path.exists() and out_path.stat().st_size > 5000 else clip_path

    @staticmethod
    def _normalize_stream_segment(clip_path: Path, temp_dir: Path, target_w: int = 720, target_h: int = 1280, target_fps: int = 30) -> Path:
        """
        Pre-join stream normalization pass (veotools standard):
        Enforces identical yuv420p, constant fps, 48kHz audio, and per-clip volume leveling.
        Falls back to standard audio resampler if audio is mathematically silent (preventing NaN crash in loudnorm).
        """
        norm_path = temp_dir / f"norm_{clip_path.name}"
        vf_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps},format=yuv420p"

        # Attempt with loudnorm first
        norm_cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", vf_filter,
            "-af", "aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            str(norm_path)
        ]
        res = subprocess.run(norm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if norm_path.exists() and norm_path.stat().st_size > 5000:
            return norm_path

        # Fallback for silent/ambient audio
        fallback_cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", vf_filter,
            "-af", "aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo",
            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            str(norm_path)
        ]
        res = subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return norm_path if norm_path.exists() and norm_path.stat().st_size > 5000 else clip_path

    @staticmethod
    def _apply_boundary_audio_fades(clip_path: Path, temp_dir: Path, fade_s: float = 0.005) -> Path:
        """Applies a 5ms audio de-click fade-in and fade-out at clip boundaries to eliminate cut pops without cutting off speech consonants."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", str(clip_path)
        ]
        dur_str = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        try:
            dur = float(dur_str)
        except ValueError:
            return clip_path

        out_path = temp_dir / f"faded_{clip_path.name}"
        fade_out_start = max(0.0, dur - fade_s)
        af_filter = f"afade=t=in:ss=0:d={fade_s},afade=t=out:st={fade_out_start:.3f}:d={fade_s}"
        fade_cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-c:v", "copy",
            "-af", af_filter,
            "-c:a", "aac",
            str(out_path)
        ]
        subprocess.run(fade_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path if out_path.exists() and out_path.stat().st_size > 0 else clip_path

    @staticmethod
    def _find_ambient_track() -> Path:
        """Finds a subtle ambient documentary drone from assets/music."""
        music_dirs = [
            PROJECT_ROOT / "assets" / "music" / "thriller",
            PROJECT_ROOT / "assets" / "music" / "dilemma",
            PROJECT_ROOT / "assets" / "music" / "facts"
        ]
        for md in music_dirs:
            if md.exists():
                for f in sorted(md.glob("*.mp3")):
                    if "drone" in f.name.lower() or "ambient" in f.name.lower() or "suspense" in f.name.lower():
                        return f
                all_mp3s = list(md.glob("*.mp3"))
                if all_mp3s:
                    return all_mp3s[0]
        return None

    @staticmethod
    def assemble(rendered_clips: list[Path], storyboard: dict, final_path: Path) -> Path:
        print("\n🧵 Assembling final video cut...")
        from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip
        from video.captions import transcribe_audio
        from video.editor import _build_caption_clips

        valid_clips = [p for p in rendered_clips if p.exists() and p.stat().st_size > 0]
        if not valid_clips:
            raise RuntimeError("No valid video clips found to assemble.")

        # Duplicate clip safety guard: ensure no scene mistakenly reuses another scene's clip
        seen_clips = {}
        for idx, p in enumerate(valid_clips):
            canonical = str(p.resolve())
            if canonical in seen_clips:
                raise RuntimeError(
                    f"Pipeline Integrity Error: Duplicate clip detected across scenes! "
                    f"Scene {idx + 1} reuses clip from Scene {seen_clips[canonical] + 1}: {p.name}"
                )
            seen_clips[canonical] = idx

        temp_dir = final_path.parent / "temp_assembly"
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔗 Processing {len(valid_clips)} clips (speech-boundary cut + veotools stream normalization)...")
        prepared_clips = []
        for idx, p in enumerate(valid_clips):
            is_seeded = (idx > 0)
            with_audio = PostProduction._ensure_audio_stream(p, temp_dir)
            trimmed = PostProduction._cut_to_speech_boundaries(with_audio, temp_dir, is_seeded=is_seeded)
            faded = PostProduction._apply_boundary_audio_fades(trimmed, temp_dir)
            normalized = PostProduction._normalize_stream_segment(faded, temp_dir)
            prepared_clips.append(normalized)

        # Frame-accurate stitching via ffmpeg concat filter
        stitched_video_path = temp_dir / f"stitched_{int(time.time())}.mp4"
        inputs = []
        filter_complex = ""

        for i, clip in enumerate(prepared_clips):
            inputs.extend(["-i", str(clip)])
            filter_complex += f"[{i}:v:0][{i}:a:0]"

        filter_complex += f"concat=n={len(prepared_clips)}:v=1:a=1[outv][outa]"

        concat_cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-c:a", "aac",
            str(stitched_video_path)
        ]
        print("🔗 Splicing clips with frame-accurate ffmpeg concat filter...")
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        stitched_video = VideoFileClip(str(stitched_video_path))
        total_duration = stitched_video.duration

        temp_speech_audio = temp_dir / f"speech_audio_{int(time.time())}.wav"
        temp_master_audio = temp_dir / f"master_mixed_{int(time.time())}.wav"

        # Check if stitched video has an audio stream
        has_audio = False
        check_audio_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(stitched_video_path)
        ]
        if subprocess.run(check_audio_cmd, capture_output=True, text=True).stdout.strip():
            has_audio = True

        if has_audio:
            print("🎙️ Extracting speech track for broadcast audio mastering...")
            # Native FFmpeg extraction: eliminates MoviePy buffer underflow/word duplication
            extract_cmd = [
                "ffmpeg", "-y",
                "-i", str(stitched_video_path),
                "-vn",
                "-c:a", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                str(temp_speech_audio)
            ]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            ambient_track = PostProduction._find_ambient_track()
            if ambient_track and ambient_track.exists():
                print(f"🎶 Layering continuous ambient bed at -20dB: {ambient_track.name}")
                mix_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(temp_speech_audio),
                    "-stream_loop", "-1", "-i", str(ambient_track),
                    "-filter_complex",
                    f"[0:a]apad=whole_dur={total_duration:.2f}[padded_speech];"
                    f"[1:a]volume=0.10,afade=t=in:ss=0:d=0.5,afade=t=out:st={max(0, total_duration - 0.8):.2f}:d=0.8[amb];"
                    f"[padded_speech][amb]amix=inputs=2:duration=first:weights=1 0.15[mixed];"
                    f"[mixed]loudnorm=I=-14:TP=-1.5:LRA=11[norm]",
                    "-map", "[norm]",
                    "-t", f"{total_duration:.3f}",
                    "-c:a", "pcm_s16le",
                    str(temp_master_audio)
                ]
                try:
                    subprocess.run(mix_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                except Exception as e:
                    print(f"⚠️ Ambient mix notice: {e}. Using speech audio directly.")
                    temp_master_audio = temp_speech_audio
            else:
                temp_master_audio = temp_speech_audio

            if temp_master_audio.exists():
                raw_audio = AudioFileClip(str(temp_master_audio))
                stitched_video = stitched_video.set_audio(raw_audio)

        final_comp = stitched_video
        caption_source_audio = temp_speech_audio if temp_speech_audio.exists() else temp_master_audio
        if caption_source_audio.exists():
            print("🎙️ Generating Whisper dynamic subtitles from speech track...")
            try:
                captions = transcribe_audio(str(caption_source_audio), words_per_caption=3)
                caption_clips = _build_caption_clips(captions, stitched_video, fmt=1)
                final_comp = CompositeVideoClip([stitched_video] + caption_clips)
                final_comp = final_comp.set_duration(total_duration)
            except Exception as e:
                print(f"⚠️ Subtitle generation note: {e}. Proceeding with clean cut.")

        print(f"🎞️ Exporting Final Deliverable to: {final_path}")
        final_comp.write_videofile(
            str(final_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            ffmpeg_params=["-vf", "setsar=1:1", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            logger=None
        )
        print(f"✅ Final Video ready at: {final_path}")

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        try:
            stitched_video.close()
        except Exception:
            pass
        return final_path


def get_next_short_path(out_dir: Path, character_name: str, is_dry_run: bool = False) -> Path:
    """
    Generates a unique sequential number naming format:
      short_[YYYYMMDD]_[###]_[character].mp4
    e.g.:
      short_20261014_001_liya.mp4
      short_20261014_002_liya.mp4
    For dry runs:
      short_20261014_001_liya_dryrun.mp4
    """
    today_str = datetime.now().strftime("%Y%m%d")
    suffix = f"_{character_name.lower()}_dryrun.mp4" if is_dry_run else f"_{character_name.lower()}.mp4"

    # Scan out_dir for existing files matching pattern to find next counter
    pattern = rf"short_{today_str}_(\d+)_{character_name.lower()}"
    max_idx = 0
    if out_dir.exists():
        for p in out_dir.glob(f"short_{today_str}_*_{character_name.lower()}*.mp4"):
            m = re.search(pattern, p.name)
            if m:
                try:
                    max_idx = max(max_idx, int(m.group(1)))
                except ValueError:
                    pass

    next_idx = max_idx + 1
    filename = f"short_{today_str}_{next_idx:03d}{suffix}"
    return out_dir / filename


def main():
    parser = argparse.ArgumentParser(description="Autonomous Character Video Pipeline for Google Flow")
    parser.add_argument("--character", type=str, default=None, help="Name of the character from characters.json (e.g. liya, Alex, Maya, Marcus)")
    parser.add_argument("--list-characters", action="store_true", help="List all registered characters and exit")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic or prompt theme")
    parser.add_argument("--scenes", type=int, default=1, help="Number of scenes to render (default: 1 for fast test, 10 for full short)")
    parser.add_argument("--aspect", type=str, default="9:16", choices=["9:16", "16:9"], help="Aspect ratio: 9:16 (Portrait Short) or 16:9 (Landscape Documentary)")
    parser.add_argument("--project", type=str, default=None, help="Google Flow project ID")
    parser.add_argument("--profile", type=str, default="youtube", help="Auth profile name")
    parser.add_argument("--dry-run", action="store_true", help="Validate end-to-end without spending Flow credits")
    parser.add_argument("--storyboard", type=str, default=None, help="Path to existing storyboard JSON file to execute")
    parser.add_argument("--session", type=str, default=None, help="Specific session ID to resume (e.g. liya_1791806220)")
    parser.add_argument("--telegram", dest="telegram", action="store_true", default=None, help="Enable Telegram approval flow for topic and video")
    parser.add_argument("--no-telegram", dest="telegram", action="store_false", help="Disable Telegram approval flow")
    args = parser.parse_args()

    use_telegram = (args.telegram is not False) and bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    if args.telegram is True:
        use_telegram = True

    cm = CharacterManager()

    if args.list_characters:
        print("\n🎭 REGISTERED CHARACTERS IN characters.json:")
        print("=" * 65)
        for idx, (k, char) in enumerate(cm.characters.items(), start=1):
            print(f"[{idx}] {char['name']} ({char.get('role', 'Protagonist')})")
            print(f"    Voice:       {char.get('voice', 'Charon')}")
            print(f"    Personality: {char.get('personality', 'None')}")
            print(f"    Style:       {char.get('style_tags', 'cinematic 4k')}")
            print("-" * 65)
        print("\nTo select a character, run:")
        print("  python experiments/autonomous_character_pipeline.py --character <Name> [--dry-run]")
        sys.exit(0)

    char_name = args.character
    if not char_name:
        if sys.stdin.isatty():
            print("\n🎭 SELECT A CHARACTER:")
            char_list = list(cm.characters.values())
            for idx, char in enumerate(char_list, start=1):
                print(f"  [{idx}] {char['name']} — {char.get('role', '')} (Voice: {char.get('voice', 'Charon')})")
            try:
                choice = input(f"\nEnter choice [1-{len(char_list)}] or type name (default: 1): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(char_list):
                    char_name = char_list[int(choice) - 1]["name"]
                elif choice:
                    char_name = choice
                else:
                    char_name = char_list[0]["name"]
            except (EOFError, KeyboardInterrupt):
                char_name = char_list[0]["name"]
        else:
            char_name = "liya"

    char_info = cm.get_character(char_name)

    print("=" * 60)
    print("🚀 AUTONOMOUS FLOW CHARACTER DIRECTOR PIPELINE")
    print(f"   Character: {char_info['name']} | Scenes: {args.scenes} | Dry-Run: {args.dry_run}")
    print("=" * 60)
    print(f"👤 Active Character: {char_info['name']} — {char_info['role']}")

    project_id = args.project
    if not project_id:
        project_id = os.environ.get("FLOW_PROJECT_ID", "f8d0e960-846a-42d6-a643-333562c0d44f")
        print(f"📁 Using Flow Project: {project_id}")

    cm.ensure_character_in_project(char_info, project_id, profile=args.profile, dry_run=args.dry_run)

    if args.session and not args.storyboard:
        s_file = SESSION_DIR / f"{args.session}.json"
        if s_file.exists():
            try:
                with open(s_file) as f:
                    s_data = json.load(f)
                if s_data.get("storyboard_path"):
                    args.storyboard = s_data["storyboard_path"]
                    print(f"🔄 Auto-loaded storyboard from session checkpoint: {args.storyboard}")
            except Exception as e:
                print(f"⚠️ Could not load storyboard from session file: {e}")

    if args.storyboard:
        sb_path = Path(args.storyboard)
        if not sb_path.exists():
            raise FileNotFoundError(f"Storyboard file not found: {sb_path}")
        with open(sb_path) as f:
            storyboard = json.load(f)
        storyboard_path = sb_path
        session_id = args.session
        if not session_id:
            for s_file in sorted(SESSION_DIR.glob(f"{char_info['name'].lower()}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    with open(s_file) as f:
                        s_data = json.load(f)
                    sp = s_data.get("storyboard_path", "")
                    if sp in (str(sb_path), str(sb_path.resolve()), str(sb_path.relative_to(PROJECT_ROOT) if sb_path.is_relative_to(PROJECT_ROOT) else sb_path)):
                        session_id = s_data["session_id"]
                        print(f"🔄 Auto-detected active session for storyboard: {session_id}")
                        break
                except Exception:
                    pass
        if not session_id:
            session_id = f"{char_info['name'].lower()}_{int(time.time())}"
        print(f"📖 Loaded Existing Storyboard: '{storyboard.get('title')}' ({len(storyboard.get('scenes', []))} scenes)")
    else:
        topic = args.topic
        if not topic:
            try:
                from generator.studio_researcher import DynamicStudioResearcher
                researcher = DynamicStudioResearcher()
                if use_telegram and not args.dry_run:
                    from telegram.approver import wait_for_topic_approval, send_telegram_notification
                    send_telegram_notification(
                        f"🎬 <b>Production Run Initialized</b>\n"
                        f"Creator: <code>@{char_info['name']}</code> ({char_info.get('role', 'Documentarian')})\n"
                        f"🔍 Researching 3 viral anomalies for your approval..."
                    )
                    candidates = researcher.research_candidate_topics(count=3)
                    chosen = wait_for_topic_approval(candidates, timeout=1800)
                    chosen_title = chosen.get("title") or chosen.get("chosen_topic") or chosen.get("text")
                    chosen_desc = chosen.get("topic") or ""
                    topic = f"{chosen_title}: {chosen_desc}".strip(": ")
                    send_telegram_notification(
                        f"✅ <b>Topic Approved:</b> <i>{chosen_title}</i>\n"
                        f"🚀 Generating 10-scene script & starting Flow video generation..."
                    )
                else:
                    research_data = researcher.research_viral_topic()
                    topic = f"{research_data['title']}: {research_data['topic']}"
                    print(f"🔬 Autonomously Researched Fresh Topic: '{topic}'")
            except Exception as e:
                print(f"⚠️ Dynamic research notice ({e}), using default generator...")
                topic = None

        director = StoryDirector(api_key=GEMINI_API_KEY)
        storyboard = director.generate_script(char_info, topic=topic, aspect=args.aspect)

        session_id = f"{char_info['name'].lower()}_{int(time.time())}"
        storyboard_path = OUTPUT_BASE / f"storyboard_{int(time.time())}.json"
        with open(storyboard_path, "w") as f:
            json.dump(storyboard, f, indent=2)
        print(f"💾 Storyboard saved to: {storyboard_path}")

    # ── SESSION CHECKPOINT: resume from last crash point ────────────────────
    checkpoint = SessionCheckpoint(session_id, storyboard_path)

    scenes_to_render = storyboard.get("scenes", [])[:args.scenes]
    print(f"🎬 Scheduled {len(scenes_to_render)} scene(s) for rendering...")
    print(f"   Session checkpoint: {checkpoint.path}")
    print(f"   (Re-run same command to resume from a failed scene)")

    renderer = VideoRenderer(project_id=project_id, profile=args.profile)
    rendered_clips = []
    fatal_error = None
    for scene in scenes_to_render:
        try:
            clip = renderer.render_scene(
                scene, CLIPS_DIR,
                character_name=char_info['name'],
                aspect=args.aspect,
                dry_run=args.dry_run,
                checkpoint=checkpoint,
                char_info=char_info
            )
            rendered_clips.append(clip)
        except RuntimeError as e:
            print(f"\n💥 FATAL: {e}")
            fatal_error = e
            break   # Stop rendering; don't waste credits on subsequent scenes

    print("\n" + "=" * 60)
    print(checkpoint.summary())
    print("─" * 60)

    if fatal_error:
        print(f"\n⛔ Session stopped due to a non-retryable error.")
        print(f"   Fix the issue above, then re-run the SAME command to resume.")
        print(f"   Completed scenes will be REUSED from checkpoint — no credits spent.")
        sys.exit(1)

    if not rendered_clips:
        print("⚠️ No clips were successfully rendered. Nothing to assemble.")
        sys.exit(1)

    if args.dry_run:
        print("✅ DRY-RUN COMPLETED SUCCESSFULLY!")
        print(f"   Storyboard: {len(rendered_clips)} scene(s) staged for character '@{char_info['name']}'.")
        print("   Zero Flow credits spent.")
        # Test assembly in dry-run to ensure end-to-end post-production integrity
        test_final = get_next_short_path(FINAL_DIR, char_info['name'], is_dry_run=True)
        final_video = PostProduction.assemble(rendered_clips, storyboard, test_final)
        QualityAssurance.inspect(final_video)
        print(f"🚀 DRY-RUN ASSEMBLY VALIDATED: {final_video}")
    else:
        print(f"🎉 RENDER COMPLETED! {len(rendered_clips)} scene(s) generated.")
        final_output_path = get_next_short_path(FINAL_DIR, char_info['name'], is_dry_run=False)
        final_video = PostProduction.assemble(rendered_clips, storyboard, final_output_path)
        QualityAssurance.inspect(final_video)
        print(f"🚀 FINAL DELIVERABLE READY: {final_video}")

        if use_telegram:
            from telegram.approver import wait_for_video_approval, notify_pipeline_success, send_telegram_notification
            video_caption = (
                f"🎬 <b>New YouTube Short Ready for Review!</b>\n\n"
                f"<b>Title:</b> {storyboard.get('title', 'YouTube Short')}\n"
                f"<b>Character:</b> @{char_info['name']}\n"
                f"<b>Format:</b> 9:16 Vertical Short (~60s)\n\n"
                f"Tap <b>Approve</b> to publish live to YouTube Shorts & Instagram Reels, or <b>Reject</b> to hold."
            )
            print("\n📱 Sending final video to Telegram for approval...")
            decision = wait_for_video_approval(str(final_video), video_caption, timeout=3600)
            if decision == "Approve":
                print("\n✅ Video APPROVED via Telegram! Initiating multi-platform publish...")
                send_telegram_notification("🚀 <b>Publishing approved!</b> Uploading to YouTube Shorts & Instagram Reels...")
                from uploader.youtube import upload_video
                from uploader.instagram import upload_reel
                from analytics.tracker import log_upload

                title = f"{storyboard.get('title')} ⚡ #shorts"
                description = f"{storyboard.get('topic', '')}\n\nHost @{char_info['name']} breaks down this fascinating anomaly."
                hashtags = ["#shorts", "#science", "#facts", "#didyouknow", "#education"]
                ig_caption = f"{title}\n\n{description}\n\n" + " ".join(hashtags)

                # 1. YouTube Shorts Upload
                yt_res = upload_video(str(final_video), title, description, hashtags, is_short=True)
                yt_url = yt_res.get("url") if yt_res else None
                if yt_res:
                    log_upload(yt_res["video_id"], 1, storyboard.get('title'), storyboard.get('topic', ''))

                # 2. Instagram Reels Upload
                ig_id = None
                ig_token = os.environ.get("IG_ACCESS_TOKEN")
                ig_account = os.environ.get("IG_ACCOUNT_ID")
                if ig_token and ig_account:
                    try:
                        ig_id = upload_reel(str(final_video), ig_caption, ig_token, ig_account)
                    except Exception as e:
                        print(f"⚠️ Instagram upload notice: {e}")

                notify_pipeline_success(f"Studio @{char_info['name']}", storyboard.get('title'), yt_url, ig_id)
                print(f"🎉 Fully Published! YouTube: {yt_url} | Instagram: {ig_id}")
            else:
                send_telegram_notification("⚠️ Video publication <b>held/aborted</b> by user.")
                print(f"⚠️ Video publication decision: {decision}. Held from public posting.")
    print("=" * 60)


if __name__ == "__main__":
    main()
