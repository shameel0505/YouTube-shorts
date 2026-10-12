#!/usr/bin/env python3
"""
check_avatar_name.py
====================
Inspects the exact name of your avatar in Google Flow's @-mention dropdown.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "gflow-cli" / "profile_youtube"

def main():
    print("🔍 Reading avatar name from Google Flow...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            viewport={"width": 1280, "height": 800}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)

        if "/project/" not in page.url:
            card = page.locator("a[href*='/project/'], button:has-text('New project'), [aria-label*='project' i]").first
            if card.is_visible(timeout=4000):
                card.click()
                time.sleep(4)

        prompt_box = page.locator("flow-prompt-box [contenteditable='true'], [contenteditable='true']").first
        if prompt_box.is_visible(timeout=5000):
            prompt_box.click()
            time.sleep(0.5)
            prompt_box.type("@", delay=100)
            time.sleep(2.0)

            # Read all options in the mention picker
            options = page.locator("button.asset-item, button[role='option'], .mention-item, .cdk-overlay-container button").all_text_contents()
            clean_options = [o.strip() for o in options if o.strip()]
            print("\n" + "=" * 50)
            print(f"🎯 AVATARS / CHARACTERS FOUND IN FLOW: {clean_options}")
            print("=" * 50)
        else:
            print("❌ Could not find prompt box.")

        context.close()

if __name__ == "__main__":
    main()
