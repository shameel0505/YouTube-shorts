import requests
import json
import xml.etree.ElementTree as ET
import time
import re
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, NICHE

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

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

def get_reddit_trending(niche: str, limit: int = 10) -> list[dict]:
    target_subs = NICHE_SUBREDDITS["default"]
    for key, subs in NICHE_SUBREDDITS.items():
        if key.lower() in niche.lower():
            target_subs = subs
            break
            
    results = []
    headers = {"User-Agent": "ShortsBot/1.0 (content research)"}
    
    for sub in target_subs[:2]:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=week&limit={limit}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for p in posts:
                post_data = p.get("data", {})
                if not post_data.get("is_video", False) and post_data.get("score", 0) > 100:
                    results.append({
                        "title": post_data.get("title", ""),
                        "url": post_data.get("url", ""),
                        "score": post_data.get("score", 0),
                        "subreddit": sub
                    })
        except Exception:
            pass
        time.sleep(0.5)
        
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

def get_trending_searches(region: str = "US") -> list[str]:
    url = f"https://trends.google.com/trending/rss?geo={region}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles = []
        for item in root.findall(".//item/title"):
            if item.text:
                titles.append(item.text)
        return titles[:20]
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
            url_item = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
            try:
                item_resp = requests.get(url_item, timeout=5)
                item_resp.raise_for_status()
                story = item_resp.json()
                if story and story.get("type") == "story":
                    results.append({
                        "title": story.get("title", ""),
                        "url": story.get("url", ""),
                        "score": story.get("score", 0)
                    })
            except Exception:
                pass
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    except Exception:
        return []

def research_topic(niche: str = None) -> dict:
    niche = niche or NICHE
    print(f"🔍 Researching trending topics for: '{niche}'")
    
    print("   📡 Fetching Reddit trending posts...")
    reddit_data = get_reddit_trending(niche, limit=8)
    if reddit_data:
        reddit_str = "\n".join([f"- [{p['score']} upvotes] {p['title']}" for p in reddit_data])
    else:
        reddit_str = "None found"
        
    print("   📈 Fetching Google Trends...")
    trends_data = get_trending_searches()
    if trends_data:
        trending_str = "\n".join([f"- {t}" for t in trends_data[:10]])
    else:
        trending_str = "None found"
        
    hn_keywords = ["ai", "tech", "software", "computer", "digital"]
    if any(k in niche.lower() for k in hn_keywords):
        print("   💻 Fetching Hacker News top stories...")
        hn_data = get_hackernews_top(limit=5)
    else:
        hn_data = []
        
    if hn_data:
        hn_str = "\n".join([f"- [{p['score']} points] {p['title']}" for p in hn_data])
    else:
        hn_str = "Not applicable for this niche"
        
    wiki_str = "No Wikipedia context found"
    if reddit_data:
        title = reddit_data[0]["title"]
        search_term = re.sub(r'[^a-zA-Z0-9\s]', '', title)
        search_term = " ".join(search_term.split()[:4])
        suggestions = search_wikipedia_opensearch(search_term)
        if suggestions:
            print(f"   📚 Fetching Wikipedia: '{suggestions[0]}'")
            wiki_str = search_wikipedia(suggestions[0], sentences=6)
            
    prompt = f"""You are a research assistant for a viral YouTube Shorts channel about: {niche}

I've gathered the following raw data from trending sources:

TRENDING REDDIT POSTS:
{reddit_str}

TRENDING SEARCHES:
{trending_str}

HACKER NEWS / TECH BUZZ:
{hn_str}

WIKIPEDIA CONTEXT:
{wiki_str}

Your task:
1. Identify the SINGLE most interesting, surprising, or mind-blowing fact/topic from this data that would perform well as a 55-second YouTube Short
2. Enrich it — add specific numbers, dates, names, or comparisons that make it vivid and concrete
3. Every fact you include must be accurate and verifiable

Respond ONLY in valid JSON with no markdown fences, no explanation, nothing else:
{{
  "chosen_topic": "3-6 word topic name",
  "why_viral": "one sentence on why this hooks viewers",
  "key_facts": [
    "specific fact 1 with real numbers/data",
    "specific fact 2 with real numbers/data",
    "specific fact 3 with real numbers/data",
    "a surprising twist or counterintuitive angle"
  ],
  "hook_angle": "the single most surprising sentence to open the video with",
  "pexels_keyword": "2-3 words for visual background footage search",
  "sources_used": ["list which of: reddit, wikipedia, hackernews, trending were useful"]
}}"""

    for _ in range(3):
        try:
            response = _model.generate_content(prompt)
            text = response.text
            text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            
            data = json.loads(text)
            print(f"   ✅ Research complete: '{data.get('chosen_topic', 'Unknown')}'")
            print(f"   💡 Hook angle: {data.get('hook_angle', 'None')}")
            return data
        except Exception as e:
            time.sleep(1)
            
    return {
        "chosen_topic": "interesting technology fact",
        "why_viral": "broad appeal",
        "key_facts": [],
        "hook_angle": "",
        "pexels_keyword": niche.split()[0],
        "sources_used": [],
    }
