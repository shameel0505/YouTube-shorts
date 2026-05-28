"""
generator/researcher.py
Researches trending topics and gathers real current facts BEFORE script generation.
Uses Google Search (via Gemini's grounding), Reddit RSS, and Wikipedia — all free.

Pipeline:
  1. Find what's trending in the niche right now
  2. Gather actual facts/data about the topic
  3. Pass researched facts to script writer → grounded, current content
"""

import json
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, NICHE

genai.configure(api_key=GEMINI_API_KEY)


# ── Wikipedia search (free, no key) ───────────────────────────────────────────

def search_wikipedia(query: str, sentences: int = 5) -> str:
    """Fetch a Wikipedia summary for a topic."""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ShortsBot/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            # Return first N sentences
            parts = extract.split(". ")
            return ". ".join(parts[:sentences]) + "."
    except Exception:
        pass
    return ""


def search_wikipedia_opensearch(query: str) -> list[str]:
    """Find related Wikipedia article titles for a query."""
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": query,
            "limit": 5,
            "format": "json",
        }
        resp = requests.get(url, params=params, timeout=10,
                            headers={"User-Agent": "ShortsBot/1.0"})
        data = resp.json()
        return data[1] if len(data) > 1 else []
    except Exception:
        return []


# ── Reddit RSS (free, no auth for public feeds) ────────────────────────────────

NICHE_SUBREDDITS = {
    "AI":           ["artificial", "MachineLearning", "technology"],
    "technology":   ["technology", "Futurology", "tech"],
    "science":      ["science", "EverythingScience", "Physics"],
    "space":        ["space", "Astronomy", "astrophysics"],
    "psychology":   ["psychology", "neuroscience", "cogsci"],
    "history":      ["history", "AskHistorians", "HistoryMemes"],
    "finance":      ["economics", "personalfinance", "investing"],
    "default":      ["todayilearned", "interestingasfuck", "Damnthatsinteresting"],
}


def get_reddit_trending(niche: str, limit: int = 10) -> list[dict]:
    """
    Fetch top posts from relevant subreddits via RSS (no API key needed).
    Returns list of {title, url, score} dicts.
    """
    # Pick subreddits based on niche keywords
    subs = NICHE_SUBREDDITS.get("default", [])
    for key, subreddit_list in NICHE_SUBREDDITS.items():
        if key.lower() in niche.lower():
            subs = subreddit_list
            break

    posts = []
    for sub in subs[:2]:  # Check 2 subreddits
        try:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=week&limit={limit}"
            resp = requests.get(
                url, timeout=10,
                headers={"User-Agent": "ShortsBot/1.0 (content research)"}
            )
            if resp.status_code == 200:
                data = resp.json()
                for post in data["data"]["children"]:
                    p = post["data"]
                    if not p.get("is_video") and p.get("score", 0) > 100:
                        posts.append({
                            "title": p["title"],
                            "url": p.get("url", ""),
                            "score": p["score"],
                            "subreddit": sub,
                        })
            time.sleep(0.5)  # polite delay
        except Exception:
            pass

    # Sort by score
    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts[:limit]


# ── Google Trends via pytrends alternative (scrape-free RSS) ──────────────────

def get_trending_searches(region: str = "US") -> list[str]:
    """
    Get today's trending search topics from Google Trends RSS.
    No API key needed.
    """
    try:
        url = f"https://trends.google.com/trending/rss?geo={region}"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ShortsBot/1.0"})
        root = ET.fromstring(resp.content)
        items = root.findall(".//item/title")
        return [item.text for item in items if item.text][:20]
    except Exception:
        return []


# ── Hacker News (great for tech/AI topics) ────────────────────────────────────

def get_hackernews_top(limit: int = 10) -> list[dict]:
    """Fetch top HN stories — excellent for AI/tech niche."""
    try:
        top_ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        ).json()[:limit * 2]

        stories = []
        for story_id in top_ids[:limit]:
            try:
                story = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=5
                ).json()
                if story and story.get("type") == "story":
                    stories.append({
                        "title": story.get("title", ""),
                        "url": story.get("url", ""),
                        "score": story.get("score", 0),
                    })
            except Exception:
                pass

        return sorted(stories, key=lambda x: x["score"], reverse=True)
    except Exception:
        return []


# ── Gemini-powered research synthesis ─────────────────────────────────────────

_research_model = genai.GenerativeModel(GEMINI_MODEL)

RESEARCH_PROMPT = """
You are a research assistant for a viral YouTube Shorts channel about: {niche}

I've gathered the following raw data from trending sources:

TRENDING REDDIT POSTS:
{reddit_posts}

TRENDING SEARCHES:
{trending}

HACKER NEWS / TECH BUZZ:
{hackernews}

WIKIPEDIA CONTEXT:
{wiki_context}

Your task:
1. Identify the SINGLE most interesting, surprising, or mind-blowing fact/topic from this data
   that would perform well as a 55-second YouTube Short
2. Research it deeper — add specific numbers, dates, names, or comparisons that make it vivid
3. Make sure every fact you include is accurate and verifiable

Respond ONLY in valid JSON:
{{
  "chosen_topic": "...",
  "why_viral": "one sentence on why this will hook viewers",
  "key_facts": [
    "specific fact 1 with numbers/data",
    "specific fact 2",
    "specific fact 3",
    "surprising twist or counterintuitive angle"
  ],
  "hook_angle": "the most surprising single sentence to open with",
  "pexels_keyword": "2-3 word visual search term",
  "sources_used": ["reddit", "wikipedia", "hackernews", "trending"]
}}
"""


def research_topic(niche: str = None) -> dict:
    """
    Full research pipeline:
    1. Pull trending data from multiple free sources
    2. Use Gemini to synthesize the best angle
    3. Return structured research brief
    """
    niche = niche or NICHE
    print(f"🔍 Researching trending topics for: '{niche}'")

    # ── Gather raw data ───────────────────────────────────────────────────────
    print("   📡 Fetching Reddit trending posts...")
    reddit = get_reddit_trending(niche, limit=8)
    reddit_str = "\n".join([f"- [{p['score']} upvotes] {p['title']}" for p in reddit]) or "None found"

    print("   📈 Fetching Google Trends...")
    trending = get_trending_searches()
    trending_str = "\n".join([f"- {t}" for t in trending[:10]]) or "None found"

    hn_data = []
    if any(k in niche.lower() for k in ["ai", "tech", "software", "computer", "digital"]):
        print("   💻 Fetching Hacker News top stories...")
        hn_data = get_hackernews_top(limit=5)
    hn_str = "\n".join([f"- [{s['score']}pts] {s['title']}" for s in hn_data]) or "Not applicable for this niche"

    # Wikipedia context for top Reddit topic
    wiki_str = ""
    if reddit:
        top_topic = reddit[0]["title"]
        # Extract key noun phrase for Wikipedia
        words = re.sub(r'[^a-zA-Z0-9 ]', '', top_topic).split()
        search_term = " ".join(words[:4])
        suggestions = search_wikipedia_opensearch(search_term)
        if suggestions:
            print(f"   📚 Fetching Wikipedia: '{suggestions[0]}'")
            wiki_str = search_wikipedia(suggestions[0], sentences=6)

    if not wiki_str:
        wiki_str = "No Wikipedia context found"

    # ── Synthesize with Gemini ─────────────────────────────────────────────
    print("   🧠 Synthesizing research with Gemini...")
    prompt = RESEARCH_PROMPT.format(
        niche=niche,
        reddit_posts=reddit_str,
        trending=trending_str,
        hackernews=hn_str,
        wiki_context=wiki_str,
    )

    for attempt in range(3):
        try:
            response = _research_model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            print(f"   ✅ Research complete: '{data['chosen_topic']}'")
            print(f"   💡 Hook angle: {data['hook_angle']}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠️  Attempt {attempt+1} failed: {e}")

    # Fallback: return minimal structure so pipeline doesn't break
    return {
        "chosen_topic": "interesting technology fact",
        "why_viral": "broad appeal",
        "key_facts": [],
        "hook_angle": "",
        "pexels_keyword": niche.split()[0],
        "sources_used": [],
    }


if __name__ == "__main__":
    result = research_topic()
    print("\n" + "═" * 60)
    print(json.dumps(result, indent=2))
