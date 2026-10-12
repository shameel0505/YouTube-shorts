#!/usr/bin/env python3
"""
test_attach_avatar.py
=====================
Tests attaching MeAvatar chip in Google Flow editor via Playwright.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "gflow-cli" / "profile_youtube"

def main():
    print("🔍 Testing exact avatar click and mention chip creation in Flow...")
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
            card = page.locator("a[href*='/project/'], button:has-text('New project')").first
            if card.is_visible(timeout=4000):
                card.click()
                time.sleep(4)

        prompt_box = page.locator("flow-prompt-box [contenteditable='true'], [contenteditable='true']").first
        if prompt_box.is_visible(timeout=5000):
            prompt_box.click()
            time.sleep(0.5)
            # Clear box
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            time.sleep(0.5)

            print("1️⃣ Typing '@'...")
            prompt_box.type("@", delay=100)
            time.sleep(1.5)

            # Try clicking the MeAvatar button directly
            print("2️⃣ Clicking 'MeAvatar' option in dropdown...")
            avatar_btn = page.locator("button:has-text('MeAvatar'), [role='option']:has-text('MeAvatar')").first
            if avatar_btn.is_visible(timeout=3000):
                avatar_btn.click()
                print("✅ Clicked MeAvatar button!")
            else:
                print("⚠️ MeAvatar button not found directly, trying ArrowDown + Enter...")
                page.keyboard.press("ArrowDown")
                time.sleep(0.5)
                page.keyboard.press("Enter")

            time.sleep(1.5)

            # Read chips
            chips = page.evaluate("() => [...document.querySelectorAll('.mention-chip, [data-reference-type], button.chip-container')].map(c => c.textContent.trim())")
            print(f"🎯 MENTION CHIPS IN PROMPT BOX: {chips}")

            # Check if prompt text is intact
            page.keyboard.type(" speaking directly into the lens in minimalist studio", delay=50)
            time.sleep(3)

        context.close()

if __name__ == "__main__":
    main()
