import os
import requests
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

GITHUB_PAT = os.environ.get("GITHUB_PAT")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "shameel0505/YouTube-shorts")
WORKFLOW_ID = "auto_pipeline.yml"

def trigger_github(task: str):
    if not GITHUB_PAT:
        log.error("❌ GITHUB_PAT is not set! Cannot trigger workflow.")
        return

    log.info(f"🚀 Triggering GitHub Action workflow '{WORKFLOW_ID}' for task: {task}")
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_PAT}"
    }
    data = {
        "ref": "main",
        "inputs": {
            "task": task
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 204:
            log.info(f"✅ Successfully triggered {task}!")
        else:
            log.error(f"❌ Failed to trigger {task}. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        log.error(f"⚠️ Network error while triggering {task}: {e}")

# Scheduler setup
scheduler = BackgroundScheduler()

# === BATCH GENERATION TRIGGERS ===
# 1. Initial Generation at 06:00 UTC (10:00 AM UAE)
scheduler.add_job(
    func=trigger_github,
    trigger="cron",
    hour="06",
    minute="00",
    args=["batch"],
    id="batch_job_1"
)
# 2. First Resume Check at 06:20 UTC (10:20 AM UAE)
scheduler.add_job(
    func=trigger_github,
    trigger="cron",
    hour="06",
    minute="20",
    args=["batch"],
    id="batch_job_2"
)
# 3. Second Resume Check at 06:40 UTC (10:40 AM UAE)
scheduler.add_job(
    func=trigger_github,
    trigger="cron",
    hour="06",
    minute="40",
    args=["batch"],
    id="batch_job_3"
)

# === INSTAGRAM POST TRIGGERS ===
# Trigger exactly 1 minute after the scheduled post time
post_hours = ["09", "13", "15", "17", "21"]
for i, hr in enumerate(post_hours):
    scheduler.add_job(
        func=trigger_github,
        trigger="cron",
        hour=hr,
        minute="01",  # 1 minute after the post time just in case
        args=["ig-scheduler"],
        id=f"ig_scheduler_job_{i}"
    )

scheduler.start()

@app.route("/")
@app.route("/ping")
@app.route("/health")
def ping():
    return "Pong! Alarm clock is running.", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    log.info(f"⏰ Starting Render Alarm Clock on port {port}...")
    # use_reloader=False is crucial to avoid running the scheduler twice
    app.run(host="0.0.0.0", port=port, use_reloader=False)
