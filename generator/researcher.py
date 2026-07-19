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
    "AI":         ["artificial", "MachineLearning", "technology", "Futurology"],
    "technology": ["technology", "Futurology", "tech", "gadgets", "hardware"],
    "science":    ["science", "EverythingScience", "Physics", "biology", "askscience"],
    "space":      ["space", "Astronomy", "astrophysics", "Cosmology"],
    "psychology": ["psychology", "neuroscience", "cogsci", "behavioraleconomics"],
    "history":    ["history", "AskHistorians", "HistoryMemes", "AlternateHistory"],
    "finance":    ["economics", "personalfinance", "investing", "StockMarket"],
    "default":    ["todayilearned", "interestingasfuck", "Damnthatsinteresting", "explainlikeimfive", "Showerthoughts", "mildlyinteresting", "dataisbeautiful", "NatureIsFuckingLit"],
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

    import random
    selected_subs = random.sample(subreddits, min(3, len(subreddits)))
    for sub in selected_subs:
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

Goal: find highly engaging, fascinating facts or stories that would stop a finger from scrolling in the first 2 seconds.

STRICT FILTER: Choose topics that evoke strong emotions—whether that is awe, deep curiosity, shock, or inspiration. 
Focus on stories that feel shareable and resonate with human nature. 
Do NOT pick purely dry, informational, political, or news-cycle content.
The ideal topic makes a viewer deeply invested in the outcome or implication.

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
    Fetch historical events/butterfly effects from r/AskHistorians, r/todayilearned, and r/HistoryMemes.
    Returns a premise dict for use in generate_thriller().
    """
    print("🔍 [FORMAT 2] Researching butterfly effect premise...")

    print("   📡 Fetching history subreddits top posts (week, 100+ upvotes)...")
    posts = get_reddit_posts(
        subreddits=["AskHistorians", "todayilearned", "HistoryMemes", "UnresolvedMysteries", "CatastrophicFailure", "AlternateHistory", "MorbidReality"],
        sort="top",
        time_filter="week",
        limit=10,
        min_score=100,
    )
    posts_str = (
        "\n".join([f"- [{p['score']} upvotes | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-engagement posts found — use your own premise."
    )

    from memory.content_log import _load_log
    used_topics = [t["text"] for t in _load_log()["format2_titles"]]
    used_str = "\n".join([f"- {t}" for t in used_topics]) if used_topics else "None"

    prompt = f"""You are a content strategist for a popular educational YouTube Shorts channel focused on "The Butterfly Effect".

Below are top posts from relevant Reddit communities this week:

{posts_str}

CRITICAL: DO NOT SELECT OR ADAPT ANY OF THESE PREVIOUSLY USED PREMISES:
{used_str}

Your task: identify or synthesize the single most fascinating historical "Butterfly Effect"
premise that can be told as a complete, catchy story in a single 40-50 second episode.

Choose something with:
- A clear historical figure and a fast setup
- A catchy hook that instantly grabs attention
- A tiny, seemingly insignificant choice or event that snowballs into massive consequences
- Highly visual setting that translates well to cinematic video

Respond ONLY in valid JSON with no markdown:
{{
  "premise": "2-3 sentence story premise detailing the tiny choice and massive outcome",
  "protagonist": "historical figure name and one-line description",
  "core_mystery": "the tiny choice/mistake that caused the chain reaction",
  "setting": "vivid 1-sentence historical location/time description",
  "genre_tags": ["history", "butterfly effect", "educational"],
  "reddit_source": "subreddit and post title if adapted, or 'original'"
}}"""

    data = _call_gemini(prompt)
    if data:
        print(f"   ✅ Premise: {data.get('premise', '')[:80]}...")
        return data

    return {
        "premise": "A frustrated artist gets rejected from an art academy, setting him on a political path that would ultimately ignite World War II.",
        "protagonist": "Adolf Hitler — rejected art student",
        "core_mystery": "How a single art school rejection letter led to the deadliest conflict in human history.",
        "setting": "Academy of Fine Arts Vienna, 1907",
        "genre_tags": ["history", "butterfly effect"],
        "reddit_source": "original",
    }


# ── FORMAT 3: Moral Dilemma ───────────────────────────────────────────────────

def research_dilemma() -> dict:
    from memory.content_log import is_topic_used, _load_log
    print("🔍 [FORMAT 3] Researching cognitive bias / brain glitch...")

    print("   📡 Fetching r/psychology and r/Glitch_in_the_Matrix (week, 100+ comments)...")
    posts = get_reddit_posts(
        subreddits=["psychology", "neuroscience", "Glitch_in_the_Matrix", "HighStrangeness", "SimulationTheory", "MandelaEffect", "philosophy", "sociology"],
        sort="top",
        time_filter="week",
        limit=10,
        min_comments=100,
    )
    posts_str = (
        "\n".join([f"- [{p['comments']} comments | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-debate posts found — use your own dilemma."
    )
    
    # Load already used dilemmas globally
    used_dilemmas = [t["text"] for t in _load_log()["format3_dilemmas"]]
    used_str = "\n".join([f"- {t}" for t in used_dilemmas]) if used_dilemmas else "None"

    base_prompt = f"""You are a content strategist for an educational cognitive science YouTube Shorts channel.

Below are top posts from r/psychology and r/Glitch_in_the_Matrix this week:

{posts_str}

CRITICAL: DO NOT SELECT ANY OF THESE PREVIOUSLY USED TOPICS:
{used_str}

Your task: identify the top 5 most universal, fascinating "brain glitches" or cognitive biases.
The ideal topics:
- Are everyday phenomena everyone experiences but doesn't have a name for
- Involve perception vs reality
- Are vivid and specific
- Would genuinely make viewers say "I do that all the time!"

Respond ONLY in valid JSON with no markdown:
[
  {{
    "dilemma_seed": "2-3 sentence description of the specific cognitive bias or brain glitch",
    "value_a": "our perception",
    "value_b": "the scientific reality",
    "option_a": "how we think it works",
    "option_b": "why our brain is actually fooling us",
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
        "dilemma_seed": "You learn a new word or buy a new car, and suddenly you see it absolutely everywhere. It feels like a simulation glitch, but it's actually the Baader-Meinhof phenomenon.",
        "value_a": "perception",
        "value_b": "reality",
        "option_a": "The thing is actually appearing more often.",
        "option_b": "Your brain just started paying attention to it.",
        "closing_question": "Have you experienced this?",
        "reddit_source": "original",
    }]

def research_psychology() -> dict:
    """
    Fetch human ingenuity and genius loophole stories from Reddit.
    Returns a premise dict for use in generate_psychology().
    """
    print("🔍 [FORMAT 4] Researching genius loopholes / human ingenuity...")

    posts = get_reddit_posts(
        subreddits=["interestingasfuck", "LifeProTips", "ActLikeYouBelong", "ProRevenge", "MaliciousCompliance", "HobbyDrama", "Scams", "UnethicalLifeProTips"],
        sort="top",
        time_filter="week",
        limit=10,
        min_score=100,
    )
    posts_str = (
        "\n".join([f"- [{p['score']} upvotes | r/{p['subreddit']}] {p['title']}" for p in posts])
        if posts else "No high-engagement posts found — use your own premise."
    )

    from memory.content_log import _load_log
    used_topics = [t["text"] for t in _load_log()["format4_cases"]]
    used_str = "\n".join([f"- {t}" for t in used_topics]) if used_topics else "None"

    prompt = f"""You are a creative director for an educational YouTube Shorts channel specializing in Human Ingenuity, Brilliant Loopholes, and Outsmarting the System.

Below are top posts from relevant Reddit communities this week:

{posts_str}

CRITICAL: DO NOT SELECT OR ADAPT ANY OF THESE PREVIOUSLY USED PREMISES:
{used_str}

Your task: identify or synthesize the single most fascinating, inspiring, or clever
real-life story of extreme human ingenuity or a harmless genius caper.

Choose something with:
- An instant hook about a clever strategy, negotiation, or outsmarting a flawed system
- Deep awe or respect for the genius of the protagonist
- A visual setting that translates well to cinematic video
- A conclusion that makes viewers want to share the incredible story
- STRICTLY NO dark true crime or malicious scams.

Respond ONLY in valid JSON with no markdown:
{{
  "premise": "2-3 sentence case/story premise about the genius loophole or strategy",
  "protagonist": "protagonist name and description",
  "core_mystery": "the central clever trick, loophole, or brilliant strategy used",
  "setting": "vivid 1-sentence location/time description",
  "genre_tags": ["genius", "loophole", "truestory", "ingenuity"],
  "reddit_source": "subreddit and post title if adapted, or 'original'"
}}"""

    data = _call_gemini(prompt)
    if data:
        print(f"   ✅ Premise: {data.get('premise', '')[:80]}...")
        return data

    return {
        "premise": "A man figures out a legal loophole to buy a lifetime first-class pass for an airline and flies around the world for decades completely free.",
        "protagonist": "Jacques Vabre — professional loophole finder",
        "core_mystery": "How he carefully read the fine print of a 1981 airline promotion to get $20 million worth of flights.",
        "setting": "First Class Lounge, American Airlines, 1981",
        "genre_tags": ["loophole", "truestory", "genius"],
        "reddit_source": "original"
    }
