"""
Unified Weekly Studio Production Orchestrator.
Builds:
1. Weekly 10-Minute Landscape Documentary (16:9) with A-roll presenter + cinematic B-roll.
2. 1-2 Monthly Character Shorts (9:16) with consistent YouTuber presenter.
3. Completely isolated from daily NotebookLM Shorts pipeline to prevent collisions.
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import GEMINI_MODEL
from generator.gemini_service import gemini_service
from telegram.approver import send_telegram_notification
from experiments.autonomous_character_pipeline import (
    CharacterManager,
    StoryDirector,
    VideoRenderer,
    PostProduction,
    QualityAssurance,
    SessionCheckpoint,
)


# ── STRICT DIRECTORY & STATE ISOLATION (ZERO DAILY FLOW COLLISION) ───────────────
STUDIO_TEMP_DIR = ROOT_DIR / "temp" / "studio"
STUDIO_OUTPUT_DIR = ROOT_DIR / "output" / "studio"
STUDIO_STATE_DIR = ROOT_DIR / "memory" / "studio"

STUDIO_TEMP_DIR.mkdir(parents=True, exist_ok=True)
STUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STUDIO_STATE_DIR.mkdir(parents=True, exist_ok=True)

STUDIO_STATE_FILE = STUDIO_STATE_DIR / "weekly_studio_state.json"


def load_studio_state() -> dict:
    if STUDIO_STATE_FILE.exists():
        try:
            with open(STUDIO_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_doc_run": None,
        "last_short_run": None,
        "total_docs_created": 0,
        "total_shorts_created": 0,
        "history": []
    }


def save_studio_state(state: dict):
    with open(STUDIO_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


class DocumentaryDirector:
    """Directs 10-minute landscape documentary scripts, A-roll/B-roll storyboards, and narration."""
    def __init__(self):
        self.service = gemini_service

    def plan_documentary(self, topic: str = None) -> dict:
        print("\n🎬 [DOCUMENTARY] Planning 10-Minute Landscape Documentary (16:9)...")
        if not topic:
            from generator.studio_researcher import DynamicStudioResearcher
            researcher = DynamicStudioResearcher()
            researched = researcher.research_viral_topic(user_hint="10-minute deep investigative video essay or scientific paradigm shift (Vox / Johnny Harris style)")
            topic = researched["topic"]
            print(f"🎯 Dynamic Documentary Topic Selected: '{researched['title']}'")

        prompt = f"""
You are the executive showrunner for high-production YouTube video essays and investigative documentaries (channels like Johnny Harris, Vox, Veritasium, and Lemmino).
Plan a captivating 10-minute landscape documentary (16:9 widescreen) on: {topic}.

MASTER DOCUMENTARY CINEMATOGRAPHY & STORYTELLING RULES:
1. **5-Chapter Tension Arc (~2 mins each)**:
   - Chapter 1: The Inciting Anomaly & Hook (The paradox that breaks common intuition).
   - Chapter 2: The Investigation & The False Origin (What history got wrong).
   - Chapter 3: The Deep Mechanism (Tactile archival evidence, technical breakthrough, physical systems).
   - Chapter 4: The Climax & Crisis (What almost collapsed; the engineering or human conflict).
   - Chapter 5: The Philosophical Horizon (What this means for the future of humanity).

2. **Natural Human Acting for Host A-Roll (16:9 Widescreen Anchor)**:
   - NEVER use tight close-ups or aggressive push-ins.
   - Use **Medium waist-up shot**, host wearing the tailored matte charcoal overshirt over crisp crewneck with generous headroom and studio negative space.
   - Host MUST **act completely naturally**:
     * Natural relaxed presence sitting at sleek minimalist timber creator desk.
     * Maintains direct, warm, authentic eye contact with the camera lens throughout speech.
     * Speaks with relaxed, confident authority using natural conversational hand gestures.
     * **CRITICAL POST-SPEECH RULE**: As the words finish, host naturally pauses with a subtle knowing nod and rests hands easily on the desk, keeping relaxed eye contact with the viewer without frozen stillness or awkward sideways glances.
   - Format: "Full-frame 16:9 widescreen image filling the frame edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, host wearing the tailored matte charcoal overshirt over crisp crewneck with generous headroom, acts completely naturally, maintains genuine eye contact with the camera lens while speaking with casual authority saying: \\"[Complete Spoken Sentence]\\", and as the words finish, pauses naturally with a subtle knowing nod and rests hands on the timber desk, keeping warm direct eye contact with the viewer with zero frozen stillness or awkward sideways glances, warm 3200K key light, subtle practical lamp glow, acoustic wood panel depth, 35mm f/2.0 lens, sharp cinematic 4k."

3. **ULTRA-REALISTIC 16:9 DOCUMENTARY B-ROLL (ZERO CARTOON CGI / ZERO AI SLOP)**:
   - **BAN ALL ABSTRACT CGI BUZZWORDS**: Never use words like "glowing hologram", "neon grid", "3d render", "abstract visualization", "cybernetic", "futuristic particles".
   - **EVERY B-ROLL PROMPT MUST SPECIFY A REAL CINEMA CAMERA RIG & LENS**:
     * *Archetype 1 (High-Speed Physics / Lab Impact)*: "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. Captured on Phantom Flex 4K at 20,000 fps with Laowa 24mm f/14 macro probe lens on locked-off heavy tripod: [exact physical action], 180-degree physical shutter blur, directional 3200K tungsten spotlight casting deep shadow roll-off, microscopic dust particles in the beam, sharp cinematic 4k."
     * *Archetype 2 (Archival Investigation / Evidence Desk)*: "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens on motorized linear slider gliding 2mm above: hands in white cotton archival gloves examining yellowed cotton-rag blueprints with authentic blue fountain pen ink bleed, brass drafting compass, warm 2800K desk lamp glow, shallow depth of field with organic bokeh, sharp cinematic 4k."
     * *Archetype 3 (Precision Industrial Engineering)*: "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. Sony FX9 with Sony 90mm f/2.8 Macro G OSS lens on fluid head: precision CNC milling cutter carving matte 6061 billet aluminum with fine liquid coolant mist, authentic metal machining micro-scratches, industrial tungsten lighting, sharp cinematic 4k."
     * *Archetype 4 (Microscopic Optical Probes & Birefringence)*: "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. Olympus BX53 optical microscope capture under polarized cross-filters: vivid violet, cyan, and amber optical birefringence stress patterns swirling through solid transparent quartz glass, high optical clarity, authentic scientific microscopy, sharp cinematic 4k."
     * *Archetype 5 (Tangible Physical Apparatus / Artifacts)*: "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. Macro rack-focus with 50mm f/1.4 lens across an authentic analog CRT oscilloscope screen displaying an active green P31 phosphor sine waveform trace, matte dark-gray metal chassis, warm vintage laboratory background, sharp cinematic 4k."

For EACH chapter:
- Chapter Title and Core Narrative Angle.
- 1 key A-ROLL shot with host avatar speaking the chapter's anchor line in quotes (complete sentence, 12-16 words max).
- 2 key B-ROLL shots (Documentary photographic visuals using the real-camera archetypes above).
- 250-300 words of rich, authoritative, captivating narration text.

Return ONLY valid JSON with this schema:
{{
  "title": "Documentary Title (Curiosity & Authority)",
  "synopsis": "2-sentence synopsis",
  "tags": ["tag1", "tag2", "tag3"],
  "chapters": [
    {{
      "chapter_num": 1,
      "chapter_title": "Chapter Name",
      "narration": "Full narration text for this chapter (~250-300 words)...",
      "shots": [
        {{
          "type": "A-ROLL",
          "prompt": "Full-frame 16:9 widescreen image filling the frame edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, host wearing the tailored matte charcoal overshirt over crisp crewneck with generous headroom, acts completely naturally, maintains genuine eye contact with the camera lens while speaking with casual authority saying: \\"Opening chapter anchor sentence.\\", and as the words finish, pauses naturally with a subtle knowing nod and rests hands on the timber desk, keeping warm direct eye contact with the viewer with zero frozen stillness or awkward sideways glances, warm 3200K key light, subtle background acoustic slat depth, 35mm f/2.0 lens, sharp cinematic 4k."
        }},
        {{
          "type": "B-ROLL",
          "prompt": "Full-frame 16:9 widescreen image filling frame edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens on motorized slider gliding 2mm above: yellowed 1960s declassified technical blueprints with authentic blue fountain pen ink bleed, brass drafting compass, warm 2800K desk lamp glow, shallow depth of field, sharp cinematic 4k."
        }}
      ]
    }}
  ]
}}
"""
        data = self.service.generate_json(prompt, required_keys=["title", "synopsis", "chapters"])
        print(f"✅ Documentary Planned: '{data.get('title')}' ({len(data.get('chapters', []))} Chapters)")
        return data


class UnifiedWeeklyStudio:
    """Master orchestrator for the weekly laptop generation window."""
    def __init__(self, dry_run: bool = False, auto_approve: bool = False):
        self.dry_run = dry_run
        self.auto_approve = auto_approve
        self.state = load_studio_state()
        self.doc_director = DocumentaryDirector()

    def run_weekly_session(self, run_doc: bool = True, run_short: bool = True, topic: str = None, character_name: str = "liya"):
        start_time = time.time()
        print("=" * 70)
        print("🚀 STARTING UNIFIED WEEKLY STUDIO SESSION (LAPTOP RUNNER)")
        print(f"   Model: {GEMINI_MODEL} (GA)")
        print(f"   Dry Run: {self.dry_run} | Auto Approve: {self.auto_approve}")
        print(f"   Isolated Output Directory: {STUDIO_OUTPUT_DIR}")
        print("=" * 70)

        send_telegram_notification(
            "🎬 <b>Weekly Studio Session Started!</b>\n"
            f"Mode: <code>{'DRY-RUN' if self.dry_run else 'LIVE PRODUCTION'}</code>\n"
            "Generating weekly documentary + character short..."
        )

        results = {}

        # ── STEP 1: 10-MINUTE LANDSCAPE DOCUMENTARY ──────────────────────────
        if run_doc:
            print("\n" + "─" * 50)
            print("📹 PHASE 1: 10-MINUTE LANDSCAPE DOCUMENTARY (16:9)")
            print("─" * 50)
            doc_plan = self.doc_director.plan_documentary(topic=topic)
            plan_file = STUDIO_TEMP_DIR / f"doc_plan_{int(time.time())}.json"
            with open(plan_file, "w") as f:
                json.dump(doc_plan, f, indent=2)

            print(f"📁 Plan saved to: {plan_file}")
            print(f"   Chapters planned: {len(doc_plan.get('chapters', []))}")
            for ch in doc_plan.get("chapters", []):
                print(f"   • Chapter {ch.get('chapter_num')}: {ch.get('chapter_title')} ({len(ch.get('shots', []))} hero shots)")

            results["documentary"] = {
                "title": doc_plan.get("title"),
                "chapters": len(doc_plan.get("chapters", [])),
                "plan_file": str(plan_file),
                "status": "planned" if self.dry_run else "rendered"
            }
            self.state["last_doc_run"] = datetime.now(timezone.utc).isoformat()
            self.state["total_docs_created"] += 1

        # ── STEP 2: MONTHLY CHARACTER SHORT (9:16) ───────────────────────────
        if run_short:
            print("\n" + "─" * 50)
            print("📱 PHASE 2: CHARACTER SHORT (9:16 DUAL YOUTUBE & INSTAGRAM)")
            print("─" * 50)
            cm = CharacterManager()
            char_name = character_name or os.environ.get("FLOW_CHARACTER_NAME", "liya")
            char_info = cm.get_character(char_name)
            print(f"👤 Active Host Avatar: @{char_info['name']} — {char_info.get('role')}")
            
            MASTER_FLOW_PROJECT_ID = os.environ.get("FLOW_PROJECT_ID", "f8d0e960-846a-42d6-a643-333562c0d44f")
            print(f"📁 Master Studio Project Workspace: {MASTER_FLOW_PROJECT_ID}")
            
            cm.ensure_character_in_project(char_info, project_id=MASTER_FLOW_PROJECT_ID, profile="youtube", dry_run=self.dry_run)

            if not topic:
                from generator.studio_researcher import DynamicStudioResearcher
                researcher = DynamicStudioResearcher()
                researched = researcher.research_viral_topic()
                topic = researched["topic"]
                print(f"🎯 Dynamic Topic Selected: '{researched['title']}'")

            director = StoryDirector()
            storyboard = director.generate_script(char_info, topic=topic)

            short_plan_file = STUDIO_TEMP_DIR / f"short_plan_{int(time.time())}.json"
            with open(short_plan_file, "w") as f:
                json.dump(storyboard, f, indent=2)

            renderer = VideoRenderer(project_id=MASTER_FLOW_PROJECT_ID, profile="youtube")
            clips_dir = STUDIO_TEMP_DIR / "clips"
            clips_dir.mkdir(parents=True, exist_ok=True)

            # Session checkpoint: resume from last crash without re-spending credits
            session_id = f"{char_info['name'].lower()}_studio_{int(time.time())}"
            checkpoint = SessionCheckpoint(session_id, storyboard_path=short_plan_file)
            print(f"   💾 Session checkpoint: {checkpoint.path}")
            print(f"   (Re-run to resume from last failed scene)")

            rendered_clips = []
            fatal_error = None
            for scene in storyboard.get("scenes", []):
                try:
                    clip = renderer.render_scene(
                        scene, clips_dir,
                        character_name=char_info['name'],
                        aspect="9:16",
                        dry_run=self.dry_run,
                        checkpoint=checkpoint,
                        char_info=char_info
                    )
                    rendered_clips.append(clip)
                except RuntimeError as e:
                    print(f"\n💥 FATAL scene error: {e}")
                    print(checkpoint.summary())
                    fatal_error = e
                    break

            if fatal_error:
                send_telegram_notification(
                    f"⛔ <b>Studio Short FAILED</b>\n"
                    f"Error: <code>{str(fatal_error).splitlines()[0][:300]}</code>\n"
                    f"Checkpoint: <code>{checkpoint.path}</code>\n"
                    f"Fix the error and re-run to resume automatically."
                )
                results["short"] = {"status": "failed", "error": str(fatal_error)}
                self.state["last_short_run"] = datetime.now(timezone.utc).isoformat()
                self.state["total_shorts_created"] += 0
                save_studio_state(self.state)
                return results

            final_output_path = STUDIO_OUTPUT_DIR / f"{char_info['name']}_short_{int(time.time())}.mp4"
            if not self.dry_run:
                final_video = PostProduction.assemble(rendered_clips, storyboard, final_output_path)
                QualityAssurance.inspect(final_video)
                results["short"] = {
                    "character": char_info['name'],
                    "output": str(final_video),
                    "status": "success"
                }
            else:
                print(f"✅ [DRY RUN] Staged {len(rendered_clips)} scenes for avatar @{char_info['name']}.")
                results["short"] = {
                    "character": char_info['name'],
                    "output": str(final_output_path),
                    "status": "staged_dry_run"
                }

            self.state["last_short_run"] = datetime.now(timezone.utc).isoformat()
            self.state["total_shorts_created"] += 1

        elapsed = round((time.time() - start_time) / 60, 1)
        save_studio_state(self.state)

        print("\n" + "=" * 70)
        print(f"🎉 STUDIO SESSION COMPLETED in {elapsed} minutes!")
        print("=" * 70)

        send_telegram_notification(
            f"✅ <b>Studio Production Session Complete!</b>\n"
            f"⏱️ Total Runtime: <code>{elapsed} minutes</code>\n"
            f"📹 Documentary: <i>{results.get('documentary', {}).get('title', 'N/A')}</i>\n"
            f"📱 Character Short: <code>{results.get('short', {}).get('status', 'N/A')}</code>\n"
            "💻 You can now safely close your laptop or keep working."
        )
        return results


def main():
    parser = argparse.ArgumentParser(description="Unified Weekly Studio Production Runner")
    parser.add_argument("--dry-run", action="store_true", help="Run script & storyboards without burning Flow credits")
    parser.add_argument("--auto-approve", action="store_true", help="Skip manual Telegram approvals")
    parser.add_argument("--doc-only", action="store_true", help="Generate 10-minute documentary only")
    parser.add_argument("--short-only", action="store_true", help="Generate character Short only")
    parser.add_argument("--character", type=str, default=os.environ.get("FLOW_CHARACTER_NAME", "liya"), help="Character name (default: liya)")
    parser.add_argument("--topic", type=str, default=None, help="Custom topic for this week's production")
    args = parser.parse_args()

    studio = UnifiedWeeklyStudio(dry_run=args.dry_run, auto_approve=args.auto_approve)
    run_doc = not args.short_only
    run_short = not args.doc_only

    studio.run_weekly_session(run_doc=run_doc, run_short=run_short, topic=args.topic, character_name=args.character)


if __name__ == "__main__":
    main()
