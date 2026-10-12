#!/usr/bin/env python3
"""
inspect_flow_avatar.py
======================
Opens a headed Chrome session to Google Flow with your active profile.
Simulates typing '@' -> pressing Enter to lock your avatar chip -> typing prompt.

SAFETY GUARANTEES:
- Does NOT submit video generation.
- Spends ZERO (0) Flow credits.
- Uses ZERO (0) Gemini API keys.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "gflow-cli" / "profile_youtube"

def main():
    print("=" * 65)
    print("🔍 LAUNCHING HEADED FLOW AVATAR INSPECTOR (ZERO-CREDIT TEST)")
    print("=" * 65)
    print(f"📁 Chrome Profile: {USER_DATA_DIR}")
    print("🌐 Opening https://flow.google.com in headed Chrome...")

    if not USER_DATA_DIR.exists():
        print(f"❌ Error: Profile directory not found at {USER_DATA_DIR}")
        sys.exit(1)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1400, "height": 900}
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=60000)
        
        print("⏳ Waiting for Flow UI to load...")
        time.sleep(5)

        # Check if already in project or open first project
        if "/project/" not in page.url:
            try:
                card = page.locator("a[href*='/project/'], button:has-text('New project'), [aria-label*='project' i]").first
                if card.is_visible(timeout=4000):
                    print("📂 Opening existing project...")
                    card.click()
                    time.sleep(4)
            except Exception:
                pass

        # Locate prompt box / contenteditable in Flow editor
        print("🔍 Locating prompt editor box...")
        prompt_selectors = [
            "flow-prompt-box [contenteditable='true']",
            "flow-prompt-box textarea",
            "[contenteditable='true']",
            "textarea",
            "div.editor-content",
        ]

        locator = None
        for selector in prompt_selectors:
            try:
                loc = page.locator(selector).first
                if loc.is_visible(timeout=3000):
                    locator = loc
                    print(f"✅ Found prompt editor: {selector}")
                    break
            except Exception:
                continue

        if locator:
            locator.click()
            time.sleep(0.5)

            # Step 1: Type '@' to trigger mention popup
            print("1️⃣ Typing '@' to open avatar selection popup...")
            locator.type("@", delay=100)
            time.sleep(1.0)

            # Step 2: Press Enter to lock avatar chip into prompt
            print("2️⃣ Pressing 'Enter' to lock the avatar into the prompt box...")
            page.keyboard.press("Enter")
            time.sleep(1.0)

            # Step 3: Type space and the rest of the prompt
            print("3️⃣ Adding space and description...")
            page.keyboard.press("Space")
            time.sleep(0.3)
            locator.type("speaking directly into the camera in a modern minimalist studio, shallow depth of field, sharp cinematic 4k", delay=40)
            print("✅ Avatar chip and prompt successfully assembled!")

        print("\n" + "=" * 65)
        print("👀 BROWSER IS NOW OPEN FOR YOU TO INSPECT!")
        print("   Look at your Chrome window to verify the avatar chip is locked in.")
        print("   (Keeping browser open for 90 seconds. You can close it anytime.)")
        print("=" * 65)

        for i in range(90, 0, -5):
            print(f"   ⏳ Browser closing in {i:2d}s (or close manually)...", end="\r")
            time.sleep(5)

        print("\n✅ Inspection session complete.")
        try:
            context.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
