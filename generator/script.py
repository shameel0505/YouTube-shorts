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
import time
from config import GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_MODEL, NICHE, VIDEO_DURATION_SEC

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)
_current_key_idx = 0


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
    """Call Gemini, parse and validate JSON, track quota, and rotate keys if necessary."""
    global _current_key_idx, _model
    
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
                if len(GEMINI_API_KEYS) > 1:
                    _current_key_idx = (_current_key_idx + 1) % len(GEMINI_API_KEYS)
                    print(f"   ⏳ Key exhausted. Switching to backup key #{_current_key_idx + 1}...")
                    genai.configure(api_key=GEMINI_API_KEYS[_current_key_idx])
                    _model = genai.GenerativeModel(GEMINI_MODEL)
                    time.sleep(2)
                    continue
                else:
                    print("   ⏳ Rate limit hit! Sleeping for 60 seconds...")
                    time.sleep(60)
            else:
                print(f"   ⚠️ Gemini Error: {e}")
                time.sleep(5)
    return None


# ── FORMAT 1: Mind-Blowing Facts ─────────────────────────────────────────────

_F1_PROMPT = """You are a professional educational content developer and science/history writer. 
Your goal is to write a highly detailed, comprehensive article about the researched fact topic below.

This article will be uploaded to Google's NotebookLM to generate a video/audio overview, so it must be professional, informative, and packed with fascinating details, historical contexts, scientific mechanisms, and surprising implications.

Niche: {niche}
RESEARCHED TOPIC: {research_topic}
Key facts: {key_facts}
Hook angle: {hook_angle}

══ WRITING RULES (CRITICAL) ══
1. LENGTH: Write a comprehensive, fully developed educational essay between 300 and 500 words. Do not write a short voiceover script.
2. DETAILS: Unpack the complexity. Explain the "why" and "how". Use specific figures, scientific terms, historical names, and concrete evidence.
3. STRUCTURE:
   - Catchy Hook Introduction: You MUST open using one of these 6 styles (pick the one that fits best):
     * "Uncomfortable Truth": Make the viewer physically hyper-aware (e.g., microscopic bugs on eyelashes).
     * "Declassified": Frame it as intentionally hidden, ignored by schools, or recently uncovered.
     * "Mandela Effect": Prove a universally held memory, belief, or proverb is entirely false.
     * "Glitch in Physics": Present a phenomenon that wildly violates the laws of common sense before explaining it.
     * "Forbidden Knowledge": Warn the viewer that once they learn this fact, they can never un-see it.
     * "Historical Lie": Aggressively attack a famous historical event or figure that everyone learns in school.
   - Deep Dive Explanation: Provide context, background, and the underlying mechanisms/history.
   - Escalation/Payoff: Reveal additional layers of complexity, current research, or fascinating implications.
4. TONE: Professional, authoritative, engaging, and mind-expanding.

══ OUTPUT FORMAT ══
Respond ONLY with a strict JSON object (no markdown):
{{
  "format": "facts",
  "topic": "3-5 word internal label",
  "title": "Curiosity-gap title (under 60 chars)",
  "description": "Write a long, engaging, multi-paragraph caption that tells a compelling story, uses emojis heavily, and ends with a strong Call to Action (CTA) question to drive comments.",
  "hashtags": ["#shorts", "#facts", "6 more tags"],
  "script": "The complete, detailed 300-500 word educational article.",
  "pexels_keyword": "A highly descriptive visual B-roll prompt (e.g., 'Retro science laboratory, glowing chemical reactions, vintage 35mm film')",
  "hook_preview": "A 1-sentence hook preview."
}}"""

_F1_PROMPT_NO_RESEARCH = """You are a professional educational content developer and science/history writer.
Your goal is to write a highly detailed, comprehensive article about a mind-blowing topic in this niche.

This article will be uploaded to Google's NotebookLM to generate a video/audio overview, so it must be professional, informative, and packed with fascinating details, scientific mechanisms, and surprising implications.

Niche: {niche}

══ WRITING RULES (CRITICAL) ══
1. LENGTH: Write a comprehensive, fully developed educational essay between 300 and 500 words.
2. DETAILS: Unpack the complexity. Explain the "why" and "how". Use specific figures and evidence.
3. STRUCTURE: 
   - Catchy Hook Introduction: You MUST open using one of these 6 styles (pick the one that fits best): "Uncomfortable Truth", "Declassified", "Mandela Effect", "Glitch in Physics", "Forbidden Knowledge", or "Historical Lie".
   - Deep Dive Explanation: Provide context and mechanisms.
   - Escalation/Payoff: Reveal additional layers of complexity.
4. TONE: Professional, authoritative, and mind-expanding.

══ OUTPUT FORMAT ══
Respond ONLY with a strict JSON object (no markdown):
{{
  "format": "facts",
  "topic": "3-5 word internal label",
  "title": "Curiosity-gap title (under 60 chars)",
  "description": "Write a long, engaging, multi-paragraph caption that tells a compelling story, uses emojis heavily, and ends with a strong Call to Action (CTA) question to drive comments.",
  "hashtags": ["#shorts", "#facts", "6 more tags"],
  "script": "The complete, detailed 300-500 word educational article.",
  "pexels_keyword": "A highly descriptive visual B-roll prompt",
  "hook_preview": "A 1-sentence hook preview."
}}"""


def generate_script(niche: str = None, research: dict = None, retries: int = 3) -> dict:
    """Generate a Format 1 (Mind-Blowing Facts) article."""
    niche = niche or NICHE
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
            research_topic=research["chosen_topic"],
            key_facts=key_facts_str,
            hook_angle=research.get("hook_angle", "Start with the most surprising fact"),
            avoid_clause=avoid_clause,
        )
    else:
        prompt = _F1_PROMPT_NO_RESEARCH.format(
            niche=niche,
            avoid_clause=avoid_clause,
        )

    data = _call_gemini_for_script(prompt, ["topic", "title", "description", "hashtags", "script", "pexels_keyword"], retries)
    if not data:
        raise RuntimeError("Gemini script generation failed.")

    if research and research.get("pexels_keyword") and len(data.get("pexels_keyword", "")) < 3:
        data["pexels_keyword"] = research["pexels_keyword"]
    if data.get("topic"):
        _save_used_topic(data["topic"])
    print(f"✅ [FORMAT 1] Comprehensive Article: '{data['title']}'")
    return data


_F2_PROMPT = """You are a professional historian and educational storyteller. 
Your goal is to write a detailed, highly comprehensive true story in the style of a **{genre}**.
This story is going to be processed by Google's NotebookLM to generate an educational video discussion, so it needs to be rich in factual details, real characters, historical settings, and fascinating connections.

PREMISE: "{premise}"
Protagonist/Figure: {protagonist}
Core Catalyst/Event: {core_mystery}
Setting: {setting}
{avoid_clause}

══ WRITING RULES (CRITICAL) ══
1. LENGTH: Write a comprehensive, fully developed true story between 300 and 500 words.
2. FACTS & DETAILS: Describe the historical setting with rich, accurate details. Give depth to the real people involved, focusing on how a tiny, seemingly insignificant choice or event snowballed into massive consequences.
3. THE REVEAL: End the story by revealing the massive, world-changing impact of that tiny initial event. Leave the viewer stunned by the chain reaction.
4. TONE: Educational, catchy, awe-inspiring, and highly engaging. NOT dark or horrific.

══ OUTPUT FORMAT ══
Respond ONLY with a strict JSON object (no markdown):
{{
  "format": "thriller",
  "title": "Curiosity-gap story title (under 60 chars)",
  "description": "Write a long, engaging, multi-paragraph caption that tells a compelling story, uses emojis heavily, and ends with a strong Call to Action (CTA) question to drive comments.",
  "hashtags": ["#shorts", "#history", "#butterflyeffect", "5 more tags"],
  "script": "The complete, detailed 300-500 word true story.",
  "hook": "A 2-3 word punchy hook text for the on-screen title card",
  "pexels_keyword": "A highly descriptive visual B-roll prompt"
}}"""

def generate_thriller(research: dict = None, retries: int = 3) -> dict:
    """
    Generate a single-episode suspense/thriller story with dynamic genre and repetition prevention.
    """
    r = research or {}
    
    premise = r.get("premise", "A man buys an old mirror and notices his reflection is lagging.")
    protagonist = r.get("protagonist", "Liam")
    core_mystery = r.get("core_mystery", "What is the reflection trying to warn him about?")
    setting = r.get("setting", "A dimly lit bedroom, late night")
    
    # Avoid recent stories
    recent = _load_used_topics()
    avoid_clause = (
        f"\n\nDo NOT cover or repeat these recently used premises/plots: {', '.join(recent[-20:])}"
        if recent else ""
    )

    # Randomly select a genre style for variety
    import random
    genres = [
        "Historical Chain Reaction", 
        "Unintended Historical Consequence", 
        "A Tiny Mistake that Changed the World", 
        "The Butterfly Effect", 
        "Mind-Blowing Historical Coincidence",
        "How One Decision Altered History"
    ]
    genre = random.choice(genres)

    prompt = _F2_PROMPT.format(
        genre=genre,
        premise=premise,
        protagonist=protagonist,
        core_mystery=core_mystery,
        setting=setting,
        avoid_clause=avoid_clause
    )

    data = _call_gemini_for_script(
        prompt,
        ["title", "description", "hashtags", "script", "hook", "pexels_keyword"],
        retries=retries
    )
    
    # Save the premise/title to prevent repetition in future runs
    data["used_topic_seed"] = premise
    _save_used_topic(data.get("title", premise))
    
    print(f"✅ [FORMAT 2] Single-Episode Thriller Script ({genre}): '{data.get('title')}'")
    return data



# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

_F3_PROMPT = """You are a professional educational writer and cognitive science expert.
Your goal is to write a highly detailed, comprehensive case study describing a fascinating psychological phenomenon or "brain glitch" that everyone experiences.

This case study will be uploaded to Google's NotebookLM to generate an interactive video discussion, so it must be highly relatable, educational, and explain the science clearly.

RESEARCHED PHENOMENON:
{dilemma_seed}

Conflict: {value_a} vs {value_b}
Perception: {option_a}
Reality: {option_b}
Closing question: "{closing_question}"

══ WRITING RULES (CRITICAL) ══
1. LENGTH: Write a comprehensive, fully developed explanation between 300 and 500 words. Do not write a short voiceover script.
2. DETAILS: Build a rich, highly specific scenario using second-person ("you") to make the viewer realize they do this every day. Add scientific explanations, cognitive bias names, and everyday examples.
3. STRUCTURE:
   - Setup: Describe a highly relatable everyday situation where this glitch happens.
   - The Science: Detail exactly why our brains are wired this way (evolution, shortcuts, biases).
   - Closing Question: Conclude with the exact closing question: "{closing_question}".
4. TONE: Objective, catchy, mind-expanding, and strictly educational/non-dark.

══ OUTPUT FORMAT ══
Respond ONLY with a strict JSON object (no markdown):
{{
  "format": "dilemma",
  "topic": "3-5 word internal label",
  "title": "Curiosity-gap phenomenon title (under 60 chars)",
  "description": "Write a long, engaging, multi-paragraph caption that tells a compelling story, uses emojis heavily, and ends with a strong Call to Action (CTA) question to drive comments.",
  "hashtags": ["#shorts", "#psychology", "#brainglitch", "5 more tags"],
  "script": "The complete, detailed 300-500 word case study. Ending with the closing question.",
  "closing_question": "The exact closing question — 6 words max, ends with ?",
  "values_in_conflict": ["{value_a}", "{value_b}"]
}}"""


def generate_dilemma(research: dict = None, retries: int = 3) -> dict:
    """Generate a Format 3 (Moral Dilemma) case study."""
    r = research or {}

    prompt = _F3_PROMPT.format(
        dilemma_seed=r.get("dilemma_seed", "Your best friend asks you to lie for them."),
        value_a=r.get("value_a", "loyalty"),
        value_b=r.get("value_b", "honesty"),
        option_a=r.get("option_a", "Keep the secret."),
        option_b=r.get("option_b", "Tell the truth."),
        closing_question=r.get("closing_question", "What would you do?"),
    )

    data = _call_gemini_for_script(
        prompt,
        ["title", "script", "closing_question", "values_in_conflict"],
        retries,
    )
    print(f"✅ [FORMAT 3] Comprehensive Dilemma Case Study: '{data['title']}'")
    return data


# ── FORMAT 4: Dark Psychology & Insane Real-Life Cases ────────────────────────

_F4_PROMPT = """You are a professional case study writer and narrative strategist.
Your goal is to write a detailed, highly comprehensive true story about extreme human ingenuity, a brilliant negotiation, or a harmless genius caper in the style of a **{genre}**.

This case study will be uploaded to Google's NotebookLM to generate an educational video discussion, so it must be professional, immersive, and lay out the characters, settings, and brilliant strategies in detail.

PREMISE: "{premise}"
Protagonist/Genius: {protagonist}
Core Strategy/Loophole: {core_mystery}
Setting: {setting}
{avoid_clause}

══ WRITING RULES (CRITICAL) ══
1. LENGTH: Write a comprehensive, fully developed true story between 300 and 500 words. Do not make it a short script.
2. DETAILS: Build a rich scenario that explains exactly how the person outsmarted the system, found the loophole, or executed the brilliant strategy. Use facts, exact numbers, and historical context.
3. COMMENT-DRIVING ENDING: Conclude the story with the clever aftermath or an inspiring realization that makes viewers want to share this incredible true story.
4. TONE: Inspiring, catchy, clever, and highly engaging. NOT dark or criminal (focus on harmless capers, clever business, or legal loopholes).

══ OUTPUT FORMAT ══
Respond ONLY with a strict JSON object (no markdown):
{{
  "format": "psychology",
  "title": "Curiosity-gap case title (under 60 chars)",
  "description": "Write a long, engaging, multi-paragraph caption that tells a compelling story, uses emojis heavily, and ends with a strong Call to Action (CTA) question to drive comments.",
  "hashtags": ["#shorts", "#genius", "#truestory", "#loophole", "4 more tags"],
  "script": "The complete, detailed 300-500 word story/case study.",
  "hook": "A 2-3 word punchy hook text for the title card",
  "pexels_keyword": "A highly descriptive visual B-roll prompt"
}}"""

def generate_psychology(research: dict = None, retries: int = 3) -> dict:
    """Generate a Format 4 (Dark Psychology) story/case study with dynamic genre and repetition prevention."""
    r = research or {}
    
    premise = r.get("premise", "An imposter convinces a family he is their missing son.")
    protagonist = r.get("protagonist", "Frédéric Bourdin — a serial impostor")
    core_mystery = r.get("core_mystery", "How a master manipulator leveraged the family's grief to blind them.")
    setting = r.get("setting", "A quiet suburban home in Texas, 1997")

    # Avoid recent premises
    recent = _load_used_topics()
    avoid_clause = (
        f"\n\nDo NOT cover or repeat these recently used case premises: {', '.join(recent[-20:])}"
        if recent else ""
    )

    # Randomly select a psychology genre style for variety
    import random
    genres = [
        "Brilliant Legal Loophole", 
        "Harmless Genius Caper", 
        "Masterful Business Negotiation", 
        "Outsmarting the System", 
        "Unbelievable True Hustle",
        "Historical Big Brain Moment"
    ]
    genre = random.choice(genres)

    prompt = _F4_PROMPT.format(
        genre=genre,
        premise=premise,
        protagonist=protagonist,
        core_mystery=core_mystery,
        setting=setting,
        avoid_clause=avoid_clause
    )

    data = _call_gemini_for_script(
        prompt,
        ["title", "script", "hook", "pexels_keyword"],
        retries=retries
    )
    
    # Save the premise/title to prevent repetition in future runs
    data["used_topic_seed"] = premise
    _save_used_topic(data.get("title", premise))
    
    print(f"✅ [FORMAT 4] Dark Psychology Case study ({genre}): '{data.get('title')}'")
    return data


# ── Batch helpers ─────────────────────────────────────────────────────────────

def generate_batch(count: int = 7, niche: str = None) -> list[dict]:
    """Generate multiple Format 1 scripts."""
    results = []
    for i in range(count):
        print(f"📝 Generating script {i+1}/{count}...")
        results.append(generate_script(niche=niche))
    return results
