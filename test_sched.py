from datetime import datetime, timezone, timedelta
import json, os

def get_schedule_mapping(num_reels):
    if num_reels == 2:
        hours = [8, 20]
    mapping = []
    base_formats = ["1", "2"]
    for i in range(num_reels):
        base_fmt = base_formats[i % len(base_formats)]
        mapping.append((base_fmt, hours[i]))
    return mapping

reels_count = 2
now = datetime.now(timezone.utc)
base_date = now.replace(minute=0, second=0, microsecond=0)

last_pending_time = None
memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
pending_ig_path = os.path.join(memory_dir, "pending_ig.json")
if os.path.exists(pending_ig_path):
    with open(pending_ig_path, "r") as f:
        pending_data = json.load(f)
        for item in pending_data:
            if "schedule_time" in item:
                dt = datetime.fromisoformat(item["schedule_time"])
                if last_pending_time is None or dt > last_pending_time:
                    last_pending_time = dt

last_assigned_time = last_pending_time
min_gap_hours = max(2, min(4, 24 // (reels_count + 1)))

schedule_mapping = get_schedule_mapping(reels_count)
schedule_times = {}
fmt_list = []

for fmt_id, hour in schedule_mapping:
    target_time = base_date.replace(hour=hour)
    if target_time < now:
        target_time = now + timedelta(minutes=15)
    
    if last_assigned_time is not None:
        min_acceptable_time = last_assigned_time + timedelta(hours=min_gap_hours)
        if target_time < min_acceptable_time:
            target_time = min_acceptable_time
            
    last_assigned_time = target_time
    schedule_times[fmt_id] = target_time
    fmt_list.append(fmt_id)

print(f"Current time: {now}")
print(f"Last pending time: {last_pending_time}")
print(f"Min gap hours: {min_gap_hours}")
for k, v in schedule_times.items():
    print(f"Format {k} -> {v.isoformat()}")
