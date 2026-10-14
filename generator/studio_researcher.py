"""
Dynamic Studio Topic Researcher & Anti-Repetition Engine.
Fetches live trends, cross-references memory/used_topics.json,
and synthesizes high-retention, viral curiosity anomalies.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from generator.gemini_service import gemini_service
from generator.researcher import get_hackernews_top, get_trending_searches, search_wikipedia

NBLM_USED_TOPICS_FILE = ROOT_DIR / "memory" / "used_topics.json"
STUDIO_USED_TOPICS_FILE = ROOT_DIR / "memory" / "studio" / "used_topics.json"

def load_used_topics() -> list[str]:
    """Loads all historically used topics across all formats and studio runs."""
    all_topics = []
    
    # 1. Read NotebookLM topics (Strictly Read-Only)
    if NBLM_USED_TOPICS_FILE.exists():
        try:
            with open(NBLM_USED_TOPICS_FILE, "r") as f:
                data = json.load(f)
            for key in ["format1_topics", "format2_titles", "format3_dilemmas", "format4_cases"]:
                for item in data.get(key, []):
                    if isinstance(item, dict):
                        t = item.get("text") or item.get("title") or item.get("topic")
                        if t:
                            all_topics.append(t.strip())
                    elif isinstance(item, str):
                        all_topics.append(item.strip())
        except Exception as e:
            print(f"⚠️ Warning: Could not read NotebookLM used topics: {e}")

    # 2. Read Studio topics
    if STUDIO_USED_TOPICS_FILE.exists():
        try:
            with open(STUDIO_USED_TOPICS_FILE, "r") as f:
                s_data = json.load(f)
            for item in s_data.get("studio_topics", []):
                if isinstance(item, dict):
                    t = item.get("title") or item.get("topic")
                    if t:
                        all_topics.append(t.strip())
        except Exception as e:
            print(f"⚠️ Warning: Could not read Studio used topics: {e}")

    return all_topics

def record_used_topic(topic_title: str, topic_summary: str):
    """Permanently records the chosen topic in memory/studio/used_topics.json (Zero NotebookLM disruption)."""
    data = {"studio_topics": []}
    if STUDIO_USED_TOPICS_FILE.exists():
        try:
            with open(STUDIO_USED_TOPICS_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"studio_topics": []}
    if "studio_topics" not in data:
        data["studio_topics"] = []
    
    data["studio_topics"].append({
        "title": topic_title,
        "topic": topic_summary,
        "date": datetime.now(timezone.utc).isoformat()
    })
    
    STUDIO_USED_TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STUDIO_USED_TOPICS_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"💾 Permanently recorded in Studio memory: '{topic_title}' (Zero-Duplication Guaranteed)")

class DynamicStudioResearcher:
    """Discovers fresh, high-retention anomalies while preventing repetition."""
    def __init__(self):
        self.service = gemini_service

    def research_viral_topic(self, user_hint: str = None) -> dict:
        print("\n🔍 [RESEARCHER] Dynamically discovering fresh viral topic...")
        used = load_used_topics()
        recent_used = used[-50:] if len(used) > 50 else used
        used_bullet_list = "\n".join(f"- {u[:120]}" for u in recent_used) if recent_used else "None"

        # Gather real signals
        trend_signals = []
        try:
            gt = get_trending_searches("US")
            if gt:
                trend_signals.append("Current Google Trends: " + ", ".join(gt[:6]))
        except Exception:
            pass
        try:
            hn = get_hackernews_top(5)
            if hn:
                trend_signals.append("Top HackerNews curiosities: " + ", ".join(h.get("title", "") for h in hn[:4]))
        except Exception:
            pass

        signals_str = "\n".join(trend_signals) if trend_signals else "General curiosity & cutting-edge science"

        prompt = f"""You are the head of research for Veritasium, Vox, and Johnny Harris.
Your goal is to discover an extraordinary, viral, high-retention anomaly, paradox, or hidden reality for an educational YouTube Short.

LIVE SIGNALS:
{signals_str}

USER PREFERENCE / HINT:
{user_hint if user_hint else "Any mind-bending scientific revelation, historical anomaly, or perception paradox"}

🛑 CRITICAL MANDATE - ZERO DUPLICATION:
Do NOT select or repeat ANY of the following previously covered topics:
{used_bullet_list}
Strictly NO molten glass / Prince Rupert's drops.

CRITERIA FOR THE WINNING TOPIC:
1. **Immediate Pattern Interrupt**: The first sentence must shatter common sense within 2 seconds.
2. **Universal Fascination**: Something everyone cares about or can picture (perception, sound, biology, everyday physics, geography, psychology).
3. **Tangible Visual Proof**: Must translate to macro photography, physical lab apparatus, or high-speed documentary footage.
4. **Emotional Climax**: Has a clear "aha!" revelation at the end.

Respond ONLY in valid JSON with this schema:
{{
  "title": "Short Punchy Title (e.g. The Sound That Drives You Crazy)",
  "topic": "1-sentence summary of the core paradox and mechanism",
  "hook_preview": "The exact opening line (12-14 words max)",
  "climax_punchline": "The exact closing revelation (12-14 words max, complete sentence ending with . or ?)"
}}
"""
        data = self.service.generate_json(prompt, required_keys=["title", "topic", "hook_preview", "climax_punchline"])
        print(f"✨ Dynamic Topic Discovered: '{data['title']}'")
        print(f"   📖 Summary: {data['topic']}")
        print(f"   ⚡ Hook: {data['hook_preview']}")
        print(f"   🎯 Climax: {data['climax_punchline']}")

        # Record in memory
        record_used_topic(data["title"], data["topic"])
        return data

    def research_candidate_topics(self, count: int = 3, user_hint: str = None) -> list[dict]:
        """Discovers multiple distinct topic candidates for Telegram user selection."""
        print(f"\n🔍 [RESEARCHER] Dynamically researching {count} viral topic candidates...")
        used = load_used_topics()
        recent_used = used[-50:] if len(used) > 50 else used
        used_bullet_list = "\n".join(f"- {u[:120]}" for u in recent_used) if recent_used else "None"

        trend_signals = []
        try:
            gt = get_trending_searches("US")
            if gt:
                trend_signals.append("Current Google Trends: " + ", ".join(gt[:6]))
        except Exception:
            pass
        try:
            hn = get_hackernews_top(5)
            if hn:
                trend_signals.append("Top HackerNews curiosities: " + ", ".join(h.get("title", "") for h in hn[:4]))
        except Exception:
            pass

        signals_str = "\n".join(trend_signals) if trend_signals else "General curiosity & cutting-edge science"

        prompt = f"""You are the head of research for Veritasium, Vox, and Johnny Harris.
Propose exactly {count} distinct, extraordinary, viral curiosity anomalies, paradoxes, or hidden realities for an educational YouTube Short.

LIVE SIGNALS:
{signals_str}

USER HINT:
{user_hint if user_hint else "Mind-bending scientific revelations, everyday physics anomalies, sensory illusions, or perception paradoxes"}

🛑 ZERO DUPLICATION:
Do NOT select or repeat any of these previously covered topics:
{used_bullet_list}

Respond ONLY in valid JSON matching this schema:
{{
  "topics": [
    {{
      "title": "Short Punchy Title (e.g. Why Pure Water Won't Shock You)",
      "topic": "1-sentence summary of the core paradox and mechanism",
      "hook_preview": "The exact opening line (12-14 words max)",
      "climax_punchline": "The exact closing revelation (12-14 words max)"
    }}
  ]
}}
"""
        data = self.service.generate_json(prompt, required_keys=["topics"])
        candidates = data.get("topics", [])
        print(f"✨ Researched {len(candidates)} Candidate Topics:")
        for idx, c in enumerate(candidates, start=1):
            print(f"   [{idx}] {c.get('title')}: {c.get('topic')}")
        return candidates

if __name__ == "__main__":
    researcher = DynamicStudioResearcher()
    res = researcher.research_viral_topic()
    print("Result:", res)
