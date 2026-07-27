import re

with open("main.py", "r") as f:
    code = f.read()

# Replace run_scheduler
new_scheduler = '''def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

    # Run the powerful Time-Window Dispatcher every 15 minutes
    # It will automatically detect if it's time for a new format, or if it needs to retry a failed one!
    def tick_dispatcher():
        import subprocess
        print("⏰ Scheduler Tick: Triggering Dispatcher Check...")
        subprocess.run(["python", "main.py", "resume-check"])

    scheduler.add_job(
        func=tick_dispatcher,
        trigger="cron", minute="*/15",
        id="dispatcher_tick", name="15-Minute Dispatcher Tick",
        misfire_grace_time=3600,
    )
    
    from analytics.tracker import check_performance
    from memory.content_log import purge_old_entries
    
    scheduler.add_job(
        func=check_performance,
        trigger="cron", hour=10, minute=0,
        id="analytics_daily", name="Daily Analytics Check"
    )
    
    scheduler.add_job(
        func=purge_old_entries,
        trigger="cron", hour=1, minute=0,
        id="purge_topics", name="Purge old topics"
    )

    log("⏰ Scheduler active — Dispatcher ticking every 15 minutes to manage time windows.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler stopped.")'''

pattern = re.compile(r'def run_scheduler\(\):.*?except KeyboardInterrupt:\n        log\("Scheduler stopped\."\)', re.DOTALL)
new_code = pattern.sub(new_scheduler, code)

with open("main.py", "w") as f:
    f.write(new_code)
print("Patched scheduler!")
