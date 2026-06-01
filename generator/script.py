"""
Script generation for all three video formats using Gemini 2.5 Pro.
  Format 1 — Mind-Blowing Facts   (generate_script)
  Format 2 — Serialized Thriller  (generate_thriller)
  Format 3 — Moral Dilemma        (generate_dilemma)
"""
import json
import re
import os
import google.generativeai as genai
import quota_tracker
from config import GEMINI_API_KEY, GEMINI_MODEL, NICHE, VIDEO_DURATION_SEC

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

_USED_TOPICS_FILE = "./temp/used_topics.json"

# ── Shared TTS writing rules injected into every prompt ──────────────────────
_TTS_RULES = """
══ UNIVERSAL TTS WRITING RULES (CRITICAL — apply to every word) ══
These rules exist because this script will be spoken by a TTS voice, not read.

1. OPEN LOOP: The very first sentence must create an unanswered question or curiosity gap.
   NEVER open with context, background, or introduction.

2. PATTERN INTERRUPT every 5-7 seconds: a surprising reveal, a tonal shift,
   new info that raises the stakes, or an abrupt cut in pacing.

3. END on a hard cliffhanger, a direct question to the viewer, or a strong emotional payoff.
   Weak endings kill replays.

4. SENTENCE LENGTH: 8-10 words maximum at moments of tension. Shorter = more powerful.
   One idea per sentence. Period. Like this.

5. TEXT PAUSES: Insert ", ..." before major reveals to trigger Kokoro's natural pause.
   Example: "She opened the door, ... and the room was empty."
   Do NOT use SSML tags — Kokoro ignores them.

6. NO filler phrases: "So," / "Now," / "Well," / "Basically," / "As you can see."

7. NO weak transitions: "And then," / "After that," / "Moving on to."

8. 155 WPM target — write exactly enough words to fill the target duration.

9. NO em-dashes (—), NO parentheses, NO markdown. Clean spoken words only.

10. Contractions are natural and encouraged: "it's", "can't", "didn't", "you've".
"""

# ── Viral hook vocabulary (Format 1) ─────────────────────────────────────────
_HOOK_OPENERS = [
    "Nobody talks about this.",
    "This was hidden for decades.",
    "Scientists still can not explain this.",
    "This happens every single day and you never noticed.",
    "This should not be possible.",
    "You have been lied to about this your entire life.",
    "One person caused this. And nobody knows who.",
    "This exists. And almost nobody knows it.",
]

_REHOOK_LINES = [
    "But wait.",
    "Now it gets worse.",
    "Plot twist.",
    "Here is the part that breaks your brain.",
    "I am not done.",
    "But actually.",
    "The real reason?",
    "Nobody saw this coming.",
    "This is where it gets insane.",
]


# ── Utility helpers ───────────────────────────────────────────────────────────

def _load_used_topics() -> list:
    try:
        with open(_USED_TOPICS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_used_topic(topic: str):
    topics = _load_used_topics()
    topics.append(topic)
    topics = topics[-200:]
    os.makedirs("./temp", exist_ok=True)
    try:
        with open(_USED_TOPICS_FILE, "w") as f:
            json.dump(topics, f)
    except Exception:
        pass


def _call_gemini_for_script(prompt: str, required_keys: list, retries: int = 3) -> dict:
    """Call Gemini, parse and validate JSON, track quota."""
    for attempt in range(retries):
        try:
            quota_tracker.increment()
            response = _model.generate_content(prompt)
            text = response.text
            text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            for k in required_keys:
                if k not in data:
                    raise ValueError(f"Missing key: {k}")
            return data
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(type(e)):
                print("   ⏳ Rate limit hit! Sleeping for 60 seconds...")
                import time
                time.sleep(60)
            else:
                import time
                time.sleep(1)
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to generate valid script after {retries} attempts.") from e
    return {}


# ── FORMAT 1: Mind-Blowing Facts ─────────────────────────────────────────────

_F1_PROMPT = """You are a viral YouTube Shorts scriptwriter. Your scripts get 50M+ views.
You write for TEXT-TO-SPEECH narration — every word must sound natural when spoken aloud.

Niche: {niche}
Target: {duration} seconds at 155 WPM (~{word_count} words)

RESEARCHED TOPIC: {research_topic}
Key facts: {key_facts}
Hook angle: {hook_angle}

══ 5-BEAT VIRAL STRUCTURE ══

BEAT 1 — HOOK (first 3 seconds, 1-2 sentences MAX):
  Lead with the single most shocking or counterintuitive sentence.
  Proven hook styles:
  - "[FACT]. And nobody talks about it."
  - "This [thing] should not exist. But it does."
  - "You have been [wrong about this] your entire life."
  The hook must make the viewer physically unable to scroll.

BEAT 2 — CONTEXT (5-10 seconds):
  Fast setup. One or two sentences. No filler. Get in, get out.

BEAT 3 — ESCALATION (15-20 seconds):
  2-3 facts that each top the last.
  End with a RE-HOOK to prevent drop-off:
  "But wait." / "Now it gets worse." / "Plot twist." / "The real reason?"

BEAT 4 — TWIST (10-15 seconds):
  The counterintuitive reveal. The "wait WHAT" moment. Make it land hard.

BEAT 5 — PAYOFF (5-8 seconds):
  End with something that makes the viewer feel smart, disturbed, or in awe.
  A mind-bending final fact, rhetorical question, or dark implication.
{tts_rules}
══ OUTPUT FORMAT ══
Respond ONLY with valid JSON. No markdown. No text outside the JSON.
{{
  "format": "facts",
  "topic": "3-5 word internal label",
  "title": "Under 60 chars. Curiosity-gap. No 'shocking' or 'amazing'.",
  "description": "One punchy sentence under 100 chars.",
  "hashtags": ["#shorts", "#facts", "6 more relevant tags"],
  "script": "The full spoken script. Clean spoken words only.",
  "pexels_keyword": "A 3-5 word descriptive phrase combining the topic title and visual elements for a highly specific image search",
  "hook_preview": "Copy the exact first sentence."
}}{avoid_clause}"""

_F1_PROMPT_NO_RESEARCH = """You are a viral YouTube Shorts scriptwriter. Your scripts get 50M+ views.
You write for TEXT-TO-SPEECH narration — every word must sound natural when spoken aloud.

Niche: {niche}
Target: {duration} seconds at 155 WPM (~{word_count} words)

══ 5-BEAT VIRAL STRUCTURE ══

BEAT 1 — HOOK (first 3 seconds):
  The most shocking counterintuitive fact about this niche.
  - "[FACT]. And nobody talks about it."
  - "This [thing] should not exist. But it does."
  - "You have been [wrong] your entire life."

BEAT 2 — CONTEXT (5-10 seconds): Fast setup. No filler.

BEAT 3 — ESCALATION (15-20 seconds):
  2-3 facts, each bigger. End with:
  "But wait." / "Now it gets worse." / "Plot twist." / "I am not done."

BEAT 4 — TWIST (10-15 seconds): The "wait WHAT" moment.

BEAT 5 — PAYOFF (5-8 seconds): Lingering fact, mind-bender, or rhetorical question.
{tts_rules}
Respond ONLY with valid JSON. No markdown. No text outside the JSON.
{{
  "format": "facts",
  "topic": "3-5 word internal label",
  "title": "Under 60 chars. Curiosity-gap. No 'shocking' or 'amazing'.",
  "description": "One punchy sentence under 100 chars.",
  "hashtags": ["#shorts", "#facts", "6 more relevant tags"],
  "script": "The full spoken script. Clean spoken words only.",
  "pexels_keyword": "A 3-5 word descriptive phrase combining the topic title and visual elements for a highly specific image search",
  "hook_preview": "Copy the exact first sentence."
}}{avoid_clause}"""


def generate_script(niche: str = None, research: dict = None, retries: int = 3) -> dict:
    """Generate a Format 1 (Mind-Blowing Facts) script."""
    niche = niche or NICHE
    word_count = int((VIDEO_DURATION_SEC / 60) * 155)
    recent = _load_used_topics()
    avoid_clause = (
        f"\n\nDo NOT cover these recently used topics: {', '.join(recent[-20:])}"
        if recent else ""
    )

    if research and research.get("chosen_topic"):
        facts = research.get("key_facts", [])
        key_facts_str = "".join([f"  • {f}\n" for f in facts]) if facts else "  • Use verified supporting facts\n"
        prompt = _F1_PROMPT.format(
            niche=niche,
            duration=VIDEO_DURATION_SEC,
            word_count=word_count,
            research_topic=research["chosen_topic"],
            key_facts=key_facts_str,
            hook_angle=research.get("hook_angle", "Start with the most surprising fact"),
            tts_rules=_TTS_RULES,
            avoid_clause=avoid_clause,
        )
    else:
        prompt = _F1_PROMPT_NO_RESEARCH.format(
            niche=niche,
            duration=VIDEO_DURATION_SEC,
            word_count=word_count,
            tts_rules=_TTS_RULES,
            avoid_clause=avoid_clause,
        )

    data = _call_gemini_for_script(prompt, ["topic", "title", "description", "hashtags", "script", "pexels_keyword"], retries)
    if research and research.get("pexels_keyword") and len(data.get("pexels_keyword", "")) < 3:
        data["pexels_keyword"] = research["pexels_keyword"]
    _save_used_topic(data["topic"])
    print(f"✅ [FORMAT 1] Script: '{data['title']}'")
    return data


# ── FORMAT 2: Serialized Thriller ─────────────────────────────────────────────

_F2_PROMPT_NEW = """You are a serialized thriller scriptwriter for YouTube Shorts.
Each episode is 30-40 seconds (~{word_count} words at 155 WPM).
This is PART 1 of a new story.

STORY PREMISE:
{premise}

Protagonist: {protagonist}
Core mystery: {core_mystery}
Setting: {setting}

CLIFFHANGER STYLE FOR THIS PART: {cliffhanger_style}
(Your ending MUST use this specific type of cliffhanger.)

══ STRUCTURE ══
0-5s   HOOK: Open mid-action or with a shocking statement. No setup. No introduction.
5-25s  ESCALATION: Build tension through tight, vivid descriptive sentences.
       Each sentence raises the stakes. No resolution. No answers given.
25-35s CLIFFHANGER: Hard cut at the moment of MAXIMUM tension.
       The viewer must NOT know what happens next.
       Forbidden: any hint of resolution, safety, or explanation.
Last spoken line MUST be: "Come back tomorrow to find out what happens."
{tts_rules}
══ CLIFFHANGER STYLE GUIDE ══
physical peril      — character in immediate physical danger, outcome unknown
shocking revelation — a fact is revealed that recontextualises everything
moral crossroads    — character must choose between two devastating options, NOW
ticking clock       — a deadline is revealed with seconds or hours remaining

══ OUTPUT FORMAT ══
Respond ONLY with valid JSON. No markdown. No text outside the JSON.
{{
  "format": "thriller",
  "part_number": 1,
  "story_title": "4-6 word series title (no 'The Mystery of...')",
  "title": "Series Title — Part 1 (under 60 chars)",
  "description": "Tense one-liner under 100 chars. Ends with a question or ellipsis.",
  "hashtags": ["#shorts", "#thriller", "#mystery", "5 more relevant tags"],
  "script": "Full spoken script. Ends with 'Come back tomorrow to find out what happens.'",
  "cliffhanger": "Copy the exact cliffhanger moment — the last sentence BEFORE the come-back line.",
  "characters": ["protagonist name", "any other named characters"],
  "unresolved_thread": "One sentence: what question is left unanswered?"
}}"""

_F2_PROMPT_CONTINUING = """You are a serialized thriller scriptwriter for YouTube Shorts.
Each episode is 30-40 seconds (~{word_count} words at 155 WPM).
This is PART {part_number} of an ongoing story.

STORY SO FAR (summary):
{story_so_far}

Characters: {characters}
Last part ended with this cliffhanger: "{last_cliffhanger}"
Unresolved thread: {unresolved_thread}

CLIFFHANGER STYLE FOR THIS PART: {cliffhanger_style}
(Your ending MUST use this specific type of cliffhanger — different from the last part.)

══ STRUCTURE ══
0-5s   RECAP: One sentence only. Remind viewers of the last cliffhanger. Raise the tension immediately.
5-25s  ESCALATION: Continue the story. Build tension. Raise stakes. No resolution. No answers.
       Add one new complication that makes things worse.
25-35s CLIFFHANGER: Hard cut at maximum tension. Do NOT resolve anything.
       The cliffhanger must be different in style from the previous part.
Last spoken line MUST be: "Come back tomorrow to find out what happens."
{tts_rules}
══ STRICT RULES ══
- This part must NOT feel complete or resolved on its own.
- Do NOT answer the previous cliffhanger directly — deepen the mystery instead.
- Do NOT introduce more than one new plot element per part.
- Vary sentence rhythm: mix very short (3-4 word) punches with longer tension-building lines.

══ OUTPUT FORMAT ══
Respond ONLY with valid JSON. No markdown. No text outside the JSON.
{{
  "format": "thriller",
  "part_number": {part_number},
  "story_title": "{story_title}",
  "title": "{story_title} — Part {part_number} (under 60 chars)",
  "description": "Tense one-liner under 100 chars.",
  "hashtags": ["#shorts", "#thriller", "#mystery", "5 more relevant tags"],
  "script": "Full spoken script. Ends with 'Come back tomorrow to find out what happens.'",
  "cliffhanger": "Copy the exact cliffhanger moment.",
  "characters": ["list all named characters"],
  "unresolved_thread": "One sentence: what is still unanswered?"
}}"""


def generate_thriller(research: dict = None, retries: int = 3) -> dict:
    """
    Generate a full 7-part Serialized Thriller script in one go.
    """
    word_count = int((35 / 60) * 155)  # ~90 words for 35s
    r = research or {}
    
    premise = r.get("premise", "A stranger wakes with no memory in a locked room.")

    prompt = f"""You are a viral YouTube Shorts and TikTok thriller writer. Your stories hook viewers instantly and keep them on the edge of their seats.

Take this premise: "{premise}"

Write a complete serialized story broken into EXACTLY 7 parts.
Each part must be 30 to 40 seconds when read aloud (~{word_count} words).

NARRATION & HOOKING RULES (CRITICAL):
- HOOK FAST: The first sentence of EVERY part MUST be a massive hook. Open in the middle of extreme action, a chilling realization, or a shocking dialogue line. No boring exposition.
- PACING: Use short, punchy sentences. Avoid long, complex phrasing. This is for fast-paced text-to-speech.
- HIGH TENSION: Every single sentence must raise the stakes. Make it visceral and gripping.
- SHOW, DON'T TELL: Don't say "She was scared." Say "Her pulse pounded in her throat as the lock clicked."
- CLIFFHANGERS: Each part MUST end on a brutal cliffhanger at the exact moment of maximum tension. Cut it off right before the outcome is revealed.
- Vary cliffhanger styles across parts (physical peril, shocking revelation, moral crossroads, ticking clock).
- The final part (Part 7) must provide a satisfying, mind-bending resolution.
- Length constraint: {int(word_count * 0.9)} to {int(word_count * 1.1)} words per part.

Respond ONLY with a strict JSON object containing:
{{
  "story_title": "Title of the story",
  "story_premise": "The premise used",
  "total_parts": 7,
  "parts": [
    {{
      "part_number": 1,
      "script_text": "The full spoken text for this part.",
      "cliffhanger_summary": "Summary of the cliffhanger.",
      "recap_line": "A single sentence recap to be used at the START of the next part. (Leave empty for part 7)"
    }},
    ... (all 7 parts)
  ]
}}"""

    data = _call_gemini_for_script(prompt, ["story_title", "story_premise", "total_parts", "parts"], retries=retries)
    if data and "parts" in data and len(data["parts"]) == 7:
        print(f"✅ [FORMAT 2] Story Arc Generated: '{data.get('story_title')}' — 7 parts.")
        return data

    print("⚠️ Format 2 Gemini generation failed or returned invalid parts. Using fallback.")
    return {
        "story_title": "The Locked Room",
        "story_premise": premise,
        "total_parts": 7,
        "parts": [
            {
                "part_number": i,
                "script_text": f"This is fallback part {i}. The mystery deepens.",
                "cliffhanger_summary": "A shadow appears.",
                "recap_line": "Previously, the mystery deepened."
            } for i in range(1, 8)
        ]
    }


# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

_F3_PROMPT = """You are a moral dilemma scriptwriter for YouTube Shorts.
Each video is 30-40 seconds (~{word_count} words at 155 WPM).

RESEARCHED DILEMMA:
{dilemma_seed}

Values in conflict: {value_a} vs {value_b}
Option A: {option_a}
Option B: {option_b}
Closing question: "{closing_question}"

══ STRUCTURE (MANDATORY) ══

0-10s  SCENARIO SETUP — second person ("you"), vivid and specific:
  Place the viewer inside the situation immediately.
  Use sensory detail. Make it feel REAL.
  Open with action or conflict — NOT background or introduction.

10-30s CONFLICT — present both options clearly and fairly:
  Describe what each choice means and costs.
  Do NOT imply which is correct.
  Do NOT editorialize. Do NOT moralize.
  Both options must seem equally defensible to reasonable people.

30-40s CLOSING QUESTION — spoken aloud, then fades to on-screen text:
  Speak the exact closing question: "{closing_question}"
  This is the FINAL line of the script. Nothing after it.
{tts_rules}
══ ABSOLUTE RULES ══
- NO resolution. NO moral lesson. NO "the right answer is..."
- NO language that implies one choice is better: "obviously", "clearly", "anyone would"
- Topics must pit widely held values against each other — not right vs wrong
- The scenario must be specific enough that viewers argue in comments
- The closing question must be 6 words or fewer

══ OUTPUT FORMAT ══
Respond ONLY with valid JSON. No markdown. No text outside the JSON.
{{
  "format": "dilemma",
  "topic": "3-5 word internal label",
  "title": "Under 60 chars. Ends with a question mark. Frames the dilemma clearly.",
  "description": "One punchy sentence under 100 chars. Ends with ?",
  "hashtags": ["#shorts", "#moraldilemma", "#wouldyourather", "5 more relevant tags"],
  "script": "Full spoken script. Final line is exactly the closing question.",
  "closing_question": "The exact on-screen question text — 6 words max, ends with ?",
  "values_in_conflict": ["{value_a}", "{value_b}"]
}}"""


def generate_dilemma(research: dict = None, retries: int = 3) -> dict:
    """Generate a Format 3 (Moral Dilemma) script."""
    word_count = int((35 / 60) * 155)  # ~90 words for 35s
    r = research or {}

    prompt = _F3_PROMPT.format(
        word_count=word_count,
        dilemma_seed=r.get("dilemma_seed", "Your best friend asks you to lie for them."),
        value_a=r.get("value_a", "loyalty"),
        value_b=r.get("value_b", "honesty"),
        option_a=r.get("option_a", "Keep the secret."),
        option_b=r.get("option_b", "Tell the truth."),
        closing_question=r.get("closing_question", "What would you do?"),
        tts_rules=_TTS_RULES,
    )

    data = _call_gemini_for_script(
        prompt,
        ["title", "script", "closing_question", "values_in_conflict"],
        retries,
    )
    print(f"✅ [FORMAT 3] Script: '{data['title']}'")
    print(f"   Closing Q: {data.get('closing_question', '')}")
    return data


# ── Batch helpers ─────────────────────────────────────────────────────────────

def generate_batch(count: int = 7, niche: str = None) -> list[dict]:
    """Generate multiple Format 1 scripts."""
    results = []
    for i in range(count):
        print(f"📝 Generating script {i+1}/{count}...")
        results.append(generate_script(niche=niche))
    return results
