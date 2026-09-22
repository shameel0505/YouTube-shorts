"""
Weekly Telegram Reminder for YouTube Studio Production Runs.
Can be run locally via cron/launchd or remotely via GitHub Actions cron.
Dispatches an actionable status ping to the user's Telegram chat.
"""
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

# Load local environment if present
load_dotenv()

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    GEMINI_MODEL,
    NICHE,
)
import quota_tracker


def send_weekly_reminder(dry_run: bool = False) -> bool:
    """Send formatted weekly reminder to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from environment.")
        return False

    used_quota = quota_tracker.get_used()
    quota_limit = quota_tracker.GEMINI_QUOTA_LIMIT

    message = (
        "⏰ <b>WEEKLY YOUTUBE STUDIO REMINDER</b>\n\n"
        "Hey Shameel! It's time for your weekly video production session.\n\n"
        "📊 <b>System Status:</b>\n"
        f"• Active Model: <code>{GEMINI_MODEL}</code> (GA)\n"
        f"• Gemini Quota: <code>{used_quota}/{quota_limit} calls used today</code>\n"
        f"• Production Niche: <code>{NICHE}</code>\n"
        "• Flow Web Credits: Ready for Veo 2 A-roll & B-roll (~980 credits)\n\n"
        "🎬 <b>Queued Deliverables:</b>\n"
        "1. <b>10-Minute Landscape Documentary</b> (YouTube 16:9, Scheduled)\n"
        "2. <b>Creator Short</b> (YouTube Shorts 9:16 + Instagram Reels)\n\n"
        "🚀 <b>One-Step Run Command:</b>\n"
        "Open your laptop terminal and run:\n"
        "<code>source venv/bin/activate &amp;&amp; python -m experiments.unified_weekly_studio</code>\n\n"
        "<i>Estimated runtime: ~25–35 minutes while you grab a coffee ☕</i>"
    )

    if dry_run:
        print("=== [DRY RUN] TELEGRAM REMINDER MESSAGE ===")
        print(message)
        print("==========================================")
        return True

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if data.get("ok"):
            print("✅ Weekly Telegram reminder dispatched successfully!")
            return True
        else:
            print(f"❌ Telegram API returned error: {data}")
            return False
    except Exception as e:
        print(f"❌ Failed to reach Telegram API: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send weekly YouTube Studio Telegram reminder")
    parser.add_argument("--dry-run", action="store_true", help="Print message without sending")
    args = parser.parse_args()

    success = send_weekly_reminder(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
