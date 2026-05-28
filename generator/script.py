import json
import re
import os
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, NICHE, VIDEO_DURATION_SEC

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

_USED_TOPICS_FILE = "./temp/used_topics.json"

SCRIPT_PROMPT = """You are a viral YouTube Shorts scriptwriter. Your job is to write an extremely engaging,
fact-based 55-second spoken narration that hooks viewers in the first 2 seconds and keeps
them watching to the end.

Niche: {niche}
Target spoken duration: {duration} seconds (~{word_count} words at natural speaking pace)

RESEARCHED TOPIC:
Topic: {research_topic}

Key verified facts to weave in:
{key_facts}

Best hook angle to open with:
{hook_angle}

WRITING RULES — follow every one:
1. Open IMMEDIATELY with the hook angle above. Adapt its wording to be even punchier.
2. DO NOT open with "Did you know", "Have you ever", "In today's video", or any meta-preamble.
3. Every sentence = one clear idea. Maximum 12 words per sentence.
4. Use the key facts. Make them vivid. Add comparisons: "That's the same as...", "Imagine if..."
5. Structure: Hook → Build tension/curiosity (2-3 facts) → Surprising twist → Satisfying payoff
6. End with either: a jaw-dropping final fact, OR a question that makes them think, OR "Follow for more"
7. Write ONLY the spoken words. Zero stage directions, zero [MUSIC], zero emojis, zero markdown.
8. Every single word must earn its place. No filler. No padding.
9. Sound like a knowledgeable friend, not a textbook or news anchor.
10. Include real numbers, real names, real dates — specificity builds trust.

ALSO OUTPUT (in the same JSON):
- title: YouTube video title. Under 60 chars. Curiosity-gap style. No "shocking" or "amazing".
  Good examples: "The Battery That Charges in 30 Seconds" / "Why Your Brain Lies to You Every Day"
- description: One sentence under 100 chars summarizing the video
- hashtags: Array of exactly 8 hashtags. Always include #shorts. Mix broad (#science) and specific (#AItools)
- pexels_keyword: 2-3 word search term for visually relevant background footage (concrete nouns, not abstract)
  Good: "neural network visualization" / Bad: "technology"
- topic: 3-5 word label for this video's topic (used internally to avoid repetition)
- hook_preview: Copy the first sentence of your script exactly

Respond ONLY with valid JSON. No markdown code fences. No text before or after the JSON.
{{
  "topic": "...",
  "title": "...",
  "description": "...",
  "hashtags": ["#shorts", "..."],
  "script": "...",
  "pexels_keyword": "...",
  "hook_preview": "..."
}}{avoid_clause}"""

SCRIPT_PROMPT_NO_RESEARCH = """You are a viral YouTube Shorts scriptwriter. Your job is to write an extremely engaging,
fact-based 55-second spoken narration that hooks viewers in the first 2 seconds and keeps
them watching to the end.

Niche: {niche}
Target spoken duration: {duration} seconds (~{word_count} words at natural speaking pace)

WRITING RULES — follow every one:
1. Open with the single most surprising, counterintuitive, or little-known fact about this niche.
2. DO NOT open with "Did you know", "Have you ever", "In today's video", or any meta-preamble.
3. Be specific: real numbers, real names, real dates — no vague claims like "many scientists believe"
4. Every sentence = one clear idea. Maximum 12 words per sentence.
5. Structure: Surprising hook → Build tension/curiosity → Twist → Satisfying payoff
6. End with a jaw-dropping final fact or a thought-provoking question
7. Write ONLY the spoken words. Zero stage directions, zero emojis, zero markdown.
8. No filler. No padding. Every word earns its place.
9. Sound like a knowledgeable friend, not a textbook.

ALSO OUTPUT (in the same JSON):
- title: YouTube video title. Under 60 chars. Curiosity-gap style. No "shocking" or "amazing".
  Good examples: "The Battery That Charges in 30 Seconds" / "Why Your Brain Lies to You Every Day"
- description: One sentence under 100 chars summarizing the video
- hashtags: Array of exactly 8 hashtags. Always include #shorts. Mix broad (#science) and specific (#AItools)
- pexels_keyword: 2-3 word search term for visually relevant background footage (concrete nouns, not abstract)
  Good: "neural network visualization" / Bad: "technology"
- topic: 3-5 word label for this video's topic (used internally to avoid repetition)
- hook_preview: Copy the first sentence of your script exactly

Respond ONLY with valid JSON. No markdown code fences. No text before or after the JSON.
{{
  "topic": "...",
  "title": "...",
  "description": "...",
  "hashtags": ["#shorts", "..."],
  "script": "...",
  "pexels_keyword": "...",
  "hook_preview": "..."
}}{avoid_clause}"""

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

def generate_script(niche: str = None, research: dict = None, retries: int = 3) -> dict:
    niche = niche or NICHE
    word_count = int((VIDEO_DURATION_SEC / 60) * 135)
    
    recent = _load_used_topics()
    avoid_clause = f"\n\nDo NOT cover these recently used topics: {', '.join(recent[-20:])}" if recent else ""
    
    if research and research.get("chosen_topic"):
        facts = research.get("key_facts", [])
        if facts:
            key_facts_str = "".join([f"  • {fact}\n" for fact in facts])
        else:
            key_facts_str = "  • Use your knowledge to add specific supporting facts\n"
            
        prompt = SCRIPT_PROMPT.format(
            niche=niche, 
            duration=VIDEO_DURATION_SEC, 
            word_count=word_count, 
            research_topic=research["chosen_topic"], 
            key_facts=key_facts_str, 
            hook_angle=research.get("hook_angle", "Start with the most surprising fact"),
            avoid_clause=avoid_clause
        )
    else:
        prompt = SCRIPT_PROMPT_NO_RESEARCH.format(
            niche=niche, 
            duration=VIDEO_DURATION_SEC, 
            word_count=word_count,
            avoid_clause=avoid_clause
        )

    for attempt in range(retries):
        try:
            response = _model.generate_content(prompt)
            text = response.text
            text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            
            data = json.loads(text)
            
            required_keys = ["topic", "title", "description", "hashtags", "script", "pexels_keyword"]
            for k in required_keys:
                if k not in data:
                    raise ValueError(f"Missing required key: {k}")
                    
            if research and research.get("pexels_keyword") and len(data.get("pexels_keyword", "")) < 3:
                data["pexels_keyword"] = research["pexels_keyword"]
                
            _save_used_topic(data["topic"])
            print(f"✅ Script generated: '{data['title']}'")
            return data
            
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError("Failed to generate valid script after multiple attempts.") from e

def generate_batch(count: int = 7, niche: str = None) -> list[dict]:
    results = []
    for i in range(count):
        print(f"📝 Generating script {i+1}/{count}...")
        results.append(generate_script(niche=niche))
    return results
