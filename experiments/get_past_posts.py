import json
import os
from collections import Counter
from datetime import datetime

log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "analytics", "performance_log.json"))

def summarize_past_posts():
    if not os.path.exists(log_file):
        print("Performance log not found.")
        return

    with open(log_file, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON in performance log.")
            return
            
    total_posts = len(data)
    print(f"Total past posts logged: {total_posts}\n")
    
    format_counts = Counter(item.get("format", "Unknown") for item in data)
    print("Posts by format:")
    for fmt, count in format_counts.items():
        print(f"  Format {fmt}: {count} posts")
        
    print("\nMost recent 5 posts:")
    # Sort by upload_time descending
    sorted_data = sorted(data, key=lambda x: x.get("upload_time", ""), reverse=True)
    
    for item in sorted_data[:5]:
        upload_time = item.get('upload_time')
        vid_id = item.get('video_id')
        fmt = item.get('format')
        topic = item.get('topic', '')[:80]
        print(f"- [{upload_time}] Format {fmt} | ID: {vid_id} | {topic}...")

if __name__ == "__main__":
    summarize_past_posts()
