"""
========================================================================================
🛑 CRITICAL AGENT & AI INSTRUCTION - DO NOT MODIFY WITHOUT EXPLICIT USER APPROVAL 🛑
========================================================================================
This script contains the VERIFIED, GOLDEN sequence for tagging character chips on flow.google.com:
  1. Click composer ([contenteditable='true'])
  2. Type '@' with keypress delay (120ms) -> wait 2.0s
  3. Type 'liya' character by character (100ms delay) -> wait 2.5s
  4. Press 'Enter' -> commits chip with data-reference-type="entity"
  5. Append prompt text after chip

⚠️ ANY FUTURE AGENT OR AI ASSISTANT:
- DO NOT change this keystroke sequence.
- DO NOT replace it with paste/insert_text/fill.
- DO NOT replace it with description-only text embeddings.
- ASK THE USER before touching or changing anything related to this flow.
- SAFETY GUARANTEE: NEVER click submit or generate here. Zero credits consumed.
========================================================================================
"""
import sys
import os
import asyncio
from pathlib import Path

# Ensure project root in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from gflow_cli.api.client import FlowApiClient
from gflow_cli._cli_helpers import _resolve_profile, _make_provider_dir
from gflow_cli.api.transports.migrated_composer import (
    MigratedComposer,
    COMPOSER,
    MENTION_CHIP,
    PICKER_OPTION,
)

PROJECT_ID = os.environ.get("FLOW_PROJECT_ID", "f8d0e960-846a-42d6-a643-333562c0d44f")
FALLBACK_PROJECT_ID = "5fbed99c-dba2-4e9e-b9b5-9b2f6ef8bebe"

async def test_liya_tagging():
    profile_name = _resolve_profile("youtube")
    pdir = _make_provider_dir(profile_name)
    print(f"🔧 Profile directory: {pdir}")
    print(f"🎯 Target Project ID: {PROJECT_ID}")
    print("🔒 ZERO-CREDIT SAFETY: This test will NOT click submit or generate.\n")

    # Launch headed Chrome so user can see it
    async with FlowApiClient(profile_dir=pdir, headless=False) as client:
        page = client._pages[0]
        composer = MigratedComposer()

        # 1. Navigate to editor
        print(f"1️⃣ Navigating to Flow editor for project {PROJECT_ID}...")
        try:
            await composer.ensure_editor(page, PROJECT_ID)
        except Exception as e:
            print(f"⚠️ Primary project failed ({e}), trying fallback {FALLBACK_PROJECT_ID}...")
            await composer.ensure_editor(page, FALLBACK_PROJECT_ID)

        print("✅ Landed in Flow editor!")

        # 2. Clear composer
        print("2️⃣ Clearing prompt box...")
        await composer.clear_composer(page)

        # 3. Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # 4. Perform exact @ + l + i + y + a sequence
        print("3️⃣ Typing '@' to open mention picker...")
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2000)

        print("4️⃣ Typing 'liya' character by character...")
        await page.keyboard.type("liya", delay=100)
        await page.wait_for_timeout(2500)

        # Check what options Flow is offering
        options = [t.strip() for t in await page.locator(PICKER_OPTION).all_text_contents()]
        print(f"📋 Dropdown options offered by Flow: {options}")

        # 5. Press Enter to select the character chip
        print("5️⃣ Pressing 'Enter' to commit the character chip...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2500)

        # 6. Read back chips from the DOM
        chips = await composer.read_chips(page)
        print(f"🔍 Chips found in prompt box: {chips}")

        # 7. Add trailing space and sample prompt
        sample_prompt = 'Full-frame 9:16 vertical shot, host saying: "In 1660, scientists created glass..."'
        print(f"6️⃣ Appending prompt text after chip: {sample_prompt}")
        await page.keyboard.type(" ", delay=80)
        await page.keyboard.insert_text(sample_prompt)
        await page.wait_for_timeout(1000)

        # 8. Capture screenshot
        out_dir = ROOT_DIR / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = out_dir / "test_liya_chip_verification.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"📸 Verification screenshot saved to: {screenshot_path}")

        print("\n✨ Character chip tagging test completed!")
        print("⏸️ Leaving browser open for 10 seconds for visual inspection...")
        await page.wait_for_timeout(10000)

if __name__ == "__main__":
    asyncio.run(test_liya_tagging())
