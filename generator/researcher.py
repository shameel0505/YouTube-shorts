"""
Research module — fetches trending content from Reddit, HackerNews,
Google Trends, and Wikipedia for each of the three video formats.
"""
import requests
import json
import xml.etree.ElementTree as ET
import time
import re
import google.generativeai as genai
import quota_tracker
from config import GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_MODEL, NICHE

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)
_current_key_idx = 0


# ── Niche → subreddit mapping (Format 1) ─────────────────────────────────────
NICHE_SUBREDDITS = {
    "AI":         ["artificial", "MachineLearning", "technology"],
    "technology": ["technology", "Futurology", "tech"],
    "science":    ["science", "EverythingScience", "Physics"],
    "space":      ["space", "Astronomy", "astrophysics"],
    "psychology": ["psychology", "neuroscience", "cogsci"],
    "history":    ["history", "AskHistorians", "HistoryMemes"],
    "finance":    ["economics", "personalfinance", "investing"],
    "default":    ["todayilearned", "interestingasfuck", "Damnthatsinteresting"],
}


# ── Shared HTTP helpers ───────────────────────────────────────────────────────

def search_wikipedia(query: str, sentences: int = 5) -> str:
    query = query.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
    headers = {"User-Agent": "ShortsBot/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        extract = data.get("extract", "")
        if not extract:
            return ""
        parts = extract.split(". ")
        return ". ".join(parts[:sentences]) + ("." if len(parts) >= sentences else "")
    except Exception:
        return ""


def search_wikipedia_opensearch(query: str) -> list[str]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {"action": "opensearch", "search": query, "limit": 5, "format": "json"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if len(data) > 1 and isinstance(data[1], list):
            return data[1]
        return []
    except Exception:
        return []


def get_reddit_posts(
    subreddits: list[str],
    sort: str = "top",
    time_filter: str = "week",
    limit: int = 10,
    min_score: int = 0,
    min_comments: int = 0,
) -> list[dict]:
    """
    Generic Reddit post fetcher. Returns posts meeting the score/comment thresholds.
    """
    results = []
    headers = {"User-Agent": "ShortsBot/1.0 (content research)"}

    for sub in subreddits[:3]:
        url = f"https://www.reddit.com/r/{sub}/{sort}.json?t={time_filter}&limit={limit * 2}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])
            for p in posts:
                d = p.get("data", {})
                score    = d.get("score", 0)
                comments = d.get("num_comments", 0)
                if d.get("is_video"):
                    continue
                if score < min_score or comments < min_comments:
                    continue
                results.append({
                    "title":     d.get("title", ""),
                    "selftext":  d.get("selftext", "")[:300],
                    "url":       d.get("url", ""),
                    "score":     score,
                    "comments":  comments,
                    "subreddit": sub,
                })
        except Exception:
            pass
        time.sleep(0.5)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


# Keep old name for Format 1 compatibility
def get_reddit_trending(niche: str, limit: int = 10) -> list[dict]:
    target_subs = NICHE_SUBREDDITS["default"]
    for key, subs in NICHE_SUBREDDITS.items():
        if key.lower() in niche.lower():
            target_subs = subs
            break
    return get_reddit_posts(target_subs, limit=limit, min_score=100)


def get_trending_searches(region: str = "US") -> list[str]:
    """Google Trends RSS — top 5 trending searches in the given region."""
    url = f"https://trends.google.com/trending/rss?geo={region}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles = [item.text for item in root.findall(".//item/title") if item.text]
        return titles[:5]
    except Exception:
        return []


def get_hackernews_top(limit: int = 10) -> list[dict]:
    url_top = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        resp = requests.get(url_top, timeout=10)
        resp.raise_for_status()
        ids = resp.json()[:limit * 2]
        results = []
        for item_id in ids[:limit]:
            try:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=5
                )
                item_resp.raise_for_status()
                story = item_resp.json()
                if story and story.get("type") == "story":
                    results.append({
                        "title": story.get("title", ""),
                        "url":   story.get("url", ""),
                        "score": story.get("score", 0),
                    })
            except Exception:
                pass
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    except Exception:
        return []


def _call_gemini(prompt: str) -> dict:
    """Call Gemini, parse JSON response, track quota, and rotate keys if necessary. Returns parsed dict or {}."""
    global _current_key_idx, _model
    
    for _ in range(3):
        try:
            quota_tracker.increment()
            response = _model.generate_content(prompt)
            text = response.text
            text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
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
                time.sleep(1)
    return {}



# ── FORMAT 1: Mind-Blowing Facts ─────────────────────────────────────────────

def research_topic(niche: str = None) -> dict:
    from memory.content_log import is_topic_used, _load_log
    niche = niche or NICHE
    print(f"🔍 [FORMAT 1] Researching trending topics for: '{niche}'")

    print("   📡 Fetching Reddit trending posts...")
    reddit_data = get_reddit_trending(niche, limit=8)
    reddit_str = (
        "\n".join([f"- [{p['score']} upvotes] {p['title']}" for p in reddit_data])
        if reddit_data else "None found"
    )

    print("   📈 Fetching Google Trends (top 5 US searches)...")
    trends_data = get_trending_searches()
    trends_str = (
        "\n".join([f"- {t}" for t in trends_data])
        if trends_data else "None found"
    )

    hn_keywords = ["ai", "tech", "software", "computer", "digital", "mind", "fact", "science", "space", "history"]
    if any(k in niche.lower() for k in hn_keywords):
        print("   💻 Fetching Hacker News top stories...")
        hn_data = get_hackernews_top(limit=5)
    else:
        hn_data = []
    hn_str = (
        "\n".join([f"- [{p['score']} points] {p['title']}" for p in hn_data])
        if hn_data else "Not applicable"
    )

    wiki_str = "No Wikipedia context"
    if reddit_data:
        title       = reddit_data[0]["title"]
        search_term = " ".join(re.sub(r'[^a-zA-Z0-9\s]', '', title).split()[:4])
        suggestions = search_wikipedia_opensearch(search_term)
        if suggestions:
            print(f"   📚 Fetching Wikipedia: '{suggestions[0]}'")
            wiki_str = search_wikipedia(suggestions[0], sentences=6)
            
    # Load already used topics globally
    used_topics = [t["text"] for t in _load_log()["format1_topics"]]
    used_str = "\n".join([f"- {t}" for t in used_topics]) if used_topics else "None"

    base_prompt = f"""You are a research analyst for a viral YouTube Shorts channel about: {niche}

Goal: find the single most mind-blowing, counterintuitive, or little-known fact/story that
would stop a finger from scrolling in the first 2 seconds.

STRICT FILTER: Choose topics that produce awe, surprise, or shock.
Do NOT pick purely informational, political, or news-cycle content.
The ideal topic makes a viewer say "wait, WHAT?!" — not just "oh interesting."

CRITICAL: DO NOT SELECT ANY OF THESE PREVIOUSLY USED TOPICS:
{used_str}

Raw data from trending sources:

TRENDING REDDIT POSTS (sorted by engagement):
{reddit_str}

GOOGLE TRENDS — TOP US SEARCHES TODAY:
{trends_str}

HACKER NEWS / TECH BUZZ:
{hn_str}

WIKIPEDIA CONTEXT:
{wiki_str}

Your task:
1. Pick the 5 MOST mind-blowing, counterintuitive topics likely to produce awe or shock.
2. Return them ranked from 1 to 5, where 1 is the most viral.

Respond ONLY in valid JSON with no markdown:
[
  {{
    "text": "The core fact or story (1-2 sentences)",
    "source": "Where this comes from (e.g. Hacker News, Wikipedia, Reddit, or Original)"
  }},
  ... (4 more)
]"""

    prompt = base_prompt
    for attempt in range(3):
        data = _call_gemini(prompt)
        if data and isinstance(data, list) and len(data) > 0:
            print(f"   ✅ Found {len(data)} topics.")
            return data
        else:
            prompt = base_prompt + "\n\nERROR: You must return a JSON array of 5 objects!"

    # Fallback if loop fails or exhausts options
    return [{"text": "interesting technology fact", "source": "original"}]


# ── FORMAT 2: Serialized Thriller ─────────────────────────────────────────────

def research_thriller() -> dict:
    """
    Fetch thriller/mystery/suspense premises from r/shortscarystories, r/twoSentenceHorror, and r/unresolvedmysteries.
    Returns a premise dict for use in generate_thriller().
    """
    print("🔍 [FORMAT 2] Researching thriller premise...")

    print("   📡 Fetching mystery/horror subreddits top posts (week, 100+ upvotes)...")
    posts = get_reddit_posts(
        subreddits=["shortscarystories", "twoSentenceHorror", "unresolvedmysteries"],
        sort="top",
        time_filter="week",
        limit=10,
        min_score=100,
    )
    posts_str = (
        "\n".join([f"- [{p['score']} upvotes | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-engagement posts found — use your own premise."
    )

    prompt = f"""You are a creative director for a popular single-episode YouTube Shorts mystery/thriller channel.

Below are top posts from relevant Reddit communities this week:

{posts_str}

Your task: identify or synthesize the single most tension-filled, mysterious, or suspenseful
premise that can be told as a complete, catchy story in a single 40-50 second episode.

Choose something with:
- A clear protagonist and a fast setup
- A catchy hook that instantly grabs attention
- A twist, mystery, or chilling realization that resolves within the episode
- Highly visual setting that translates well to cinematic video

Respond ONLY in valid JSON with no markdown:
{{
  "premise": "2-3 sentence story premise",
  "protagonist": "character name and one-line description",
  "core_mystery": "the central question or twist driving the story",
  "setting": "vivid 1-sentence location/time description",
  "genre_tags": ["thriller", "mystery", "suspense"],
  "reddit_source": "subreddit and post title if adapted, or 'original'"
}}"""

    data = _call_gemini(prompt)
    if data:
        print(f"   ✅ Premise: {data.get('premise', '')[:80]}...")
        return data

    return {
        "premise": "A man buys an old mirror and notices his reflection is always lagging exactly one second behind him.",
        "protagonist": "Liam — a collector of antiques",
        "core_mystery": "What is the reflection trying to warn him about before it stops lagging?",
        "setting": "A dimly lit bedroom, late night",
        "genre_tags": ["thriller", "mystery", "suspense"],
        "reddit_source": "original",
    }


# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

def research_dilemma() -> dict:
    from memory.content_log import is_topic_used, _load_log
    print("🔍 [FORMAT 3] Researching moral dilemma...")

    print("   📡 Fetching r/AmItheAsshole and r/AskReddit (week, 1000+ comments)...")
    posts = get_reddit_posts(
        subreddits=["AmItheAsshole", "AskReddit"],
        sort="top",
        time_filter="week",
        limit=10,
        min_comments=1000,
    )
    posts_str = (
        "\n".join([f"- [{p['comments']} comments | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-debate posts found — use your own dilemma."
    )
    
    # Load already used dilemmas globally
    used_dilemmas = [t["text"] for t in _load_log()["format3_dilemmas"]]
    used_str = "\n".join([f"- {t}" for t in used_dilemmas]) if used_dilemmas else "None"

    base_prompt = f"""You are a content strategist for a moral dilemma YouTube Shorts channel.

Below are top posts from r/AmItheAsshole and r/AskReddit this week, sorted by debate intensity:

{posts_str}

CRITICAL: DO NOT SELECT ANY OF THESE PREVIOUSLY USED DILEMMAS:
{used_str}

Your task: identify the top 5 most universal, emotionally charged ethical conflicts.
The ideal dilemmas:
- Have no clear "correct" answer
- Involve values like: fairness vs loyalty, honesty vs protection
- Are vivid and specific
- Would genuinely divide viewers 50/50

Respond ONLY in valid JSON with no markdown:
[
  {{
    "dilemma_seed": "2-3 sentence description of the specific situation",
    "value_a": "first value at stake",
    "value_b": "second value at stake",
    "option_a": "one plausible choice",
    "option_b": "the other plausible choice",
    "closing_question": "Exact on-screen question — 6 words max, ends with ?",
    "reddit_source": "subreddit and post title if adapted, or 'original'"
  }},
  ... (4 more)
]"""

    prompt = base_prompt
    for attempt in range(3):
        data = _call_gemini(prompt)
        if data and isinstance(data, list) and len(data) > 0:
            print(f"   ✅ Found {len(data)} dilemmas.")
            return data
        else:
            prompt = base_prompt + "\n\nERROR: You must return a JSON array of 5 objects!"

    # Fallback if loop fails or exhausts options
    return [{
        "dilemma_seed": "Your best friend confesses they cheated on their partner and asks you to keep it secret. You've known their partner for years.",
        "value_a": "loyalty",
        "value_b": "honesty",
        "option_a": "Keep the secret to protect your friendship.",
        "option_b": "Tell the partner — they deserve the truth.",
        "closing_question": "What would you do?",
        "reddit_source": "original",
    }]

def research_psychology() -> dict:
    """
    Fetch bizarre real-life stories, dark psychology cases, and social experiments from Reddit.
    Returns a premise dict for use in generate_psychology().
    """
    print("🔍 [FORMAT 4] Researching dark psychology / bizarre real-life premise...")

    posts = get_reddit_posts(
        subreddits=["todayilearned", "bizarrelife", "TrueCrime", "psychology"],
        sort="top",
        time_filter="week",
        limit=10,
        min_score=100,
    )
    posts_str = (
        "\n".join([f"- [{p['score']} upvotes | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-engagement posts found — use your own premise."
    )

    prompt = f"""You are a creative director for a popular YouTube Shorts channel specializing in Dark Psychology, Social Experiments, and Bizarre Real-Life survival stories.

Below are top posts from relevant Reddit communities this week:

{posts_str}

Your task: identify or synthesize the single most fascinating, hooking, or mind-bending
dark psychology concept, strange social experiment, or survival event that can be told as a complete, catchy story in a single 40-50 second episode.

Choose something with:
- An instant hook about human behavior, manipulation, or extreme survival
- Deep psychological tension or an unbelievable real-world survival twist
- A visual setting that translates well to cinematic video
- A conclusion that leaves viewers questioning human nature

Respond ONLY in valid JSON with no markdown:
{{
  "premise": "2-3 sentence case/story premise",
  "protagonist": "protagonist name (e.g., the manipulator, experimenter, or survivor) and description",
  "core_mystery": "the central psychological twist, manipulation trick, or survival anomaly",
  "setting": "vivid 1-sentence location/time description (e.g., 'A high-security prison lab, 1971')",
  "genre_tags": ["dark psychology", "manipulation", "survival", "experiment"],
  "reddit_source": "subreddit and post title if adapted, or 'original'"
}}"""

    data = _call_gemini(prompt)
    if data:
        print(f"   ✅ Premise: {data.get('premise', '')[:80]}...")
        return data

    return {
        "premise": "An imposter successfully convinces an entire family he is their missing 16-year-old son, despite having different colored eyes and a French accent.",
        "protagonist": "Frédéric Bourdin — a serial impostor",
        "core_mystery": "How a master manipulator leveraged the family's grief to blind them to the obvious physical differences.",
        "setting": "A quiet suburban home in Texas, 1997",
        "genre_tags": ["manipulation", "psychology", "imposter"],
        "reddit_source": "original"
    }
