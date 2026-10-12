import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from the root .env file
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path)

IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")

def fetch_instagram_posts():
    if not IG_ACCESS_TOKEN or not IG_ACCOUNT_ID:
        print("Missing IG_ACCESS_TOKEN or IG_ACCOUNT_ID in .env file.")
        return

    # Instagram Graph API endpoint for user media
    url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media"
    
    # Fetch base fields
    params = {
        "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count,media_url,shortcode",
        "access_token": IG_ACCESS_TOKEN,
        "limit": 12  # Fetch latest 12 posts
    }
    
    try:
        print(f"Fetching posts from Instagram account {IG_ACCOUNT_ID}...\n")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        posts = data.get("data", [])
        
        if not posts:
            print("No posts found on this Instagram account.")
            return
            
        print(f"Found {len(posts)} recent posts. Fetching detailed insights (viewer data)...\n")
        
        for i, post in enumerate(posts, 1):
            post_id = post.get('id')
            timestamp = post.get('timestamp', 'Unknown time')
            media_type = post.get('media_type', 'Unknown type')
            product_type = post.get('media_product_type', 'Unknown product')
            caption = post.get('caption', 'No caption')
            likes = post.get('like_count', 0)
            comments = post.get('comments_count', 0)
            permalink = post.get('permalink', 'No link')
            
            # Fetch insights for this specific post
            # Metrics depend on the type of media (e.g. REELS vs IMAGE)
            insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
            if media_type == "VIDEO" or product_type == "REELS":
                metrics = "plays,reach,saved,shares,total_interactions"
            else:
                metrics = "impressions,reach,saved,total_interactions"
                
            insights_params = {
                "metric": metrics,
                "access_token": IG_ACCESS_TOKEN
            }
            
            plays = 0
            reach = 0
            shares = 0
            saved = 0
            
            try:
                insight_resp = requests.get(insights_url, params=insights_params)
                if insight_resp.status_code == 200:
                    insight_data = insight_resp.json().get('data', [])
                    for item in insight_data:
                        name = item.get('name')
                        val = item.get('values', [{}])[0].get('value', 0)
                        if name == 'plays': plays = val
                        elif name == 'reach' or name == 'impressions': reach = val
                        elif name == 'shares': shares = val
                        elif name == 'saved': saved = val
                else:
                    # Some accounts or older media don't support certain insights
                    pass
            except Exception as e:
                pass

            
            print(f"--- Post {i} ({media_type} / {product_type}) ---")
            print(f"Date:       {timestamp}")
            print(f"Views/Plays:{plays}")
            print(f"Reach:      {reach}")
            print(f"Likes:      {likes}")
            print(f"Comments:   {comments}")
            print(f"Shares:     {shares}")
            print(f"Saved:      {saved}")
            print(f"Link:       {permalink}")
            print(f"Caption:\n{caption}\n")
            print("-" * 50)
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from Instagram API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Body: {e.response.text}")

if __name__ == "__main__":
    fetch_instagram_posts()
