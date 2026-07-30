import json

with open('memory/pending_ig.json', 'r') as f:
    posts = json.load(f)

# Keep only one post per format for today (2026-07-28)
kept_posts = []
seen_times = set()

for p in posts:
    if p['schedule_time'].startswith('2026-07-28'):
        if p['schedule_time'] not in seen_times:
            kept_posts.append(p)
            seen_times.add(p['schedule_time'])

kept_posts.sort(key=lambda x: x['schedule_time'])

with open('memory/pending_ig.json', 'w') as f:
    json.dump(kept_posts, f)

print(f"Cleaned pending_ig.json. Now has {len(kept_posts)} posts.")
for p in kept_posts:
    print(f"- {p['fmt']} @ {p['schedule_time']}")
