"""
generator/script.py
Generates short-form video scripts using Gemini 2.0 Flash (free tier).
"""

import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, NICHE, VIDEO_DURATION_SEC


genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)


SCRIPT_PROMPT = """
You are a viral YouTube Shorts scriptwriter. Your job is to create extremely engaging,
fact-based short video scripts that hook viewers in the first 2 seconds.

Niche: {niche}
Target duration: {duration} seconds of spoken content (~{word_count} words spoken aloud)

RESEARCHED TOPIC TO COVER:
Topic: {research_topic}
Key verified facts to weave in:
{key_facts}
Best hook angle: {hook_angle}

RULES:
- Start with the hook angle above — adapt it, make it even punchier
- Use the key facts — be specific, include numbers and names
- Use short punchy sentences. One idea per sentence.
- Build curiosity throughout — end with a satisfying payoff or call to action
- No filler words. Every word must earn its place.
- Write ONLY the spoken narration — no stage directions, no "[MUSIC]", no emojis
- Feel like a knowledgeable friend talking, not a textbook
- DO NOT start with "Did you know"

Also generate:
- A viral YouTube title (under 60 chars, curiosity-driven, no clickbait)
- A one-line video description (under 100 chars)
- 8 relevant hashtags (mix of broad + niche, always include #shorts)
- A Pexels search keyword (2-3 words) to find relevant background footage
- A topic label (3-5 words)

Respond ONLY with valid JSON, no markdown, no explanation:
{{
  "topic": "...",
  "title": "...",
  "description": "...",
  "hashtags": ["#shorts", "..."],
  "script": "...",
  "pexels_keyword": "...",
  "hook_preview": "first sentence only"
}}
"""

# Fallback prompt when no research data is available
SCRIPT_PROMPT_NO_RESEARCH = """
You are a viral YouTube Shorts scriptwriter. Your job is to create extremely engaging,
fact-based short video scripts that hook viewers in the first 2 seconds.

Niche: {niche}
Target duration: {duration} seconds of spoken content (~{word_count} words spoken aloud)

RULES:
- Start with a mind-blowing hook — a surprising fact or statistic. NO "Did you know" openings.
- Use short punchy sentences. One idea per sentence.
- Be specific: include real numbers, names, dates — no vague claims
- Build curiosity throughout — end with a satisfying payoff
- No filler words. Every word must earn its place.
- Write ONLY the spoken narration — no stage directions, no emojis

Also generate:
- A viral YouTube title (under 60 chars, curiosity-driven)
- A one-line video description (under 100 chars)
- 8 relevant hashtags (mix of broad + niche, always include #shorts)
- A Pexels search keyword (2-3 words) for background footage
- A topic label (3-5 words)

Respond ONLY with valid JSON, no markdown, no explanation:
{{
  "topic": "...",
  "title": "...",
  "description": "...",
  "hashtags": ["#shorts", "..."],
  "script": "...",
  "pexels_keyword": "...",
  "hook_preview": "first sentence only"
}}
"""

# Topics to avoid repeating — loaded from a simple file
_USED_TOPICS_FILE = "./temp/used_topics.json"


def _load_used_topics() -> list:
    try:
        with open(_USED_TOPICS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save_used_topic(topic: str):
    topics = _load_used_topics()
    topics.append(topic)
    # Keep last 200 only
    topics = topics[-200:]
    import os
    os.makedirs("./temp", exist_ok=True)
    with open(_USED_TOPICS_FILE, "w") as f:
        json.dump(topics, f)


def generate_script(niche: str = None, research: dict = None, retries: int = 3) -> dict:
    """
    Generate a complete video script with metadata.

    Args:
        niche:    Content niche (overrides .env NICHE)
        research: Optional research brief from researcher.py — if provided,
                  the script will be grounded in real, current, verified facts.

    Returns dict with keys: topic, title, description, hashtags,
                             script, pexels_keyword, hook_preview
    """
    niche = niche or NICHE
    word_count = int((VIDEO_DURATION_SEC / 60) * 135)  # ~135 wpm

    used = _load_used_topics()
    avoid_clause = ""
    if used:
        recent = used[-20:]
        avoid_clause = f"\n\nDo NOT cover these recently used topics: {', '.join(recent)}"

    # Use research-grounded prompt if we have a research brief
    if research and research.get("chosen_topic"):
        key_facts_str = "\n".join(
            [f"  • {f}" for f in research.get("key_facts", [])]
        ) or "  • Use your knowledge to add specific facts"

        prompt = SCRIPT_PROMPT.format(
            niche=niche,
            duration=VIDEO_DURATION_SEC,
            word_count=word_count,
            research_topic=research["chosen_topic"],
            key_facts=key_facts_str,
            hook_angle=research.get("hook_angle", "Start with the most surprising fact"),
        ) + avoid_clause
    else:
        # Fallback: no research data, use general prompt
        prompt = SCRIPT_PROMPT_NO_RESEARCH.format(
            niche=niche,
            duration=VIDEO_DURATION_SEC,
            word_count=word_count,
        ) + avoid_clause

    for attempt in range(retries):
        try:
            response = _model.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            data = json.loads(text)

            # Validate required keys
            required = ["topic", "title", "description", "hashtags", "script", "pexels_keyword"]
            for key in required:
                if key not in data:
                    raise ValueError(f"Missing key in response: {key}")

            # Inherit pexels keyword from research if script didn't produce a good one
            if research and research.get("pexels_keyword") and len(data["pexels_keyword"]) < 3:
                data["pexels_keyword"] = research["pexels_keyword"]

            _save_used_topic(data["topic"])
            print(f"✅ Script generated: '{data['title']}'")
            return data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Attempt {attempt+1} failed: {e}. Retrying...")

    raise RuntimeError("Failed to generate valid script after multiple attempts.")


def generate_batch(count: int = 7, niche: str = None) -> list[dict]:
    """Generate a week's worth of scripts in one call."""
    scripts = []
    for i in range(count):
        print(f"📝 Generating script {i+1}/{count}...")
        scripts.append(generate_script(niche=niche))
    return scripts


if __name__ == "__main__":
    result = generate_script()
    print(json.dumps(result, indent=2))
