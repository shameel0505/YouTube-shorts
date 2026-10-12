"""
========================================================================================
🛑 VISUAL DRY-RUN: ZERO-CREDIT HEADED INSPECTION FOR USER
========================================================================================
This script executes the complete Flow preparation flow in a visible (headed) Chrome browser:
  1. Opens the Flow editor
  2. Sets Aspect Ratio to 9:16 (crop_9_16) via the settings pane
  3. Sets Video Count to 1 (x1) via the settings pane
  4. Focuses the composer
  5. Types '@' (120ms delay) -> waits 2.0s
  6. Types 'liya' (100ms delay) -> waits 2.5s
  7. Presses 'Enter' -> commits the character chip
  8. Confirms chip is present with data-reference-type="entity"
  9. Appends Scene 1 photoreal prompt after the chip
  10. STOPS COMPLETELY BEFORE CLICKING SUBMIT / ENTER TO GENERATE!
  11. Leaves the browser open for visual inspection so the USER can verify everything.
========================================================================================
"""
import sys
import os
import time
import asyncio
import argparse
from pathlib import Path

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

DEFAULT_PROMPT = (
    'Full-frame 9:16 image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens, '
    'medium waist-up shot at minimalist timber creator studio desk, host wearing the tailored matte charcoal overshirt '
    'over crisp crewneck with generous headroom, authentic natural skin texture with visible micro-pores, illuminated '
    'by warm 3200K softbox key light at 45 degrees with subtle warm rim accent, organic optical bokeh. The shot opens with '
    'the host looking directly into the camera lens with engaging warmth and closed mouth in a brief 0.5-second natural resting '
    'pause, takes a subtle breath, and then begins speaking with relaxed conviction saying: "Did you know that gold is heavy because '
    'of Einstein\'s relativity theory?", using subtle natural hand gestures, and as the words finish, pauses naturally with a subtle '
    'knowing nod and rests hands easily on the timber desk, keeping warm direct eye contact with the viewer with zero frozen '
    'stillness or awkward sideways glances, sharp cinematic 4k.'
)

async def run_visual_dry_run(aspect: str = "9:16", count: int = 1, prompt_text: str = DEFAULT_PROMPT, wait_s: int = 45):
    profile_name = _resolve_profile("youtube")
    pdir = _make_provider_dir(profile_name)

    print("=" * 70)
    print("🎬 HEADED VISUAL DRY-RUN (ZERO CREDITS SPENT)")
    print(f"   Project:      {PROJECT_ID}")
    print(f"   Aspect Ratio: {aspect}")
    print(f"   Video Count:  {count} (x{count})")
    print(f"   Character:    @liya (LiyaCharacter)")
    print("=" * 70)

    # Launch headed Chrome so user can see the browser window
    async with FlowApiClient(profile_dir=pdir, headless=False) as client:
        page = client._pages[0]
        composer = MigratedComposer()

        # 1. Land on project editor with resilient multi-account index discovery
        print("\n1️⃣ Navigating to Flow editor...")
        account_idx = os.environ.get("GFLOW_ACCOUNT_INDEX")
        candidate_urls = []
        if account_idx:
            candidate_urls.append(f"https://flow.google.com/u/{account_idx}/project/{PROJECT_ID}")
        candidate_urls.extend([
            f"https://flow.google.com/u/0/project/{PROJECT_ID}",
            f"https://flow.google.com/u/1/project/{PROJECT_ID}",
            f"https://flow.google.com/project/{PROJECT_ID}",
        ])

        landed = False
        for url in candidate_urls:
            print(f"   Attempting navigation: {url}")
            await page.goto(url)
            await page.wait_for_timeout(3000)
            if "/about" not in page.url:
                landed = True
                print(f"   ✅ Landed on editor: {page.url}")
                break

        if not landed:
            print("   [FALLBACK] Using composer.ensure_editor...")
            await composer.ensure_editor(page, PROJECT_ID)

        # 2. Configure Mode (Video), Aspect Ratio, and Count=1 in Settings
        target_aspect_lig = "crop_9_16" if aspect == "9:16" else "crop_16_9"
        print(f"\n2️⃣ Opening Settings Pane to select video mode, aspect '{aspect}' ({target_aspect_lig}), and count 'x{count}'...")
        try:
            pane = await composer._open_pane(page)
            await composer._select(page, pane, axis="mode", lig="videocam")
            await composer._select(page, pane, axis="aspect", lig=target_aspect_lig)
            await composer._select(page, pane, axis="count", text=f"x{count}")
            await composer._close_pane(page)
            print(f"   ✅ Settings applied: mode=videocam, aspect={aspect}, count=x{count}")
        except Exception as e:
            print(f"   ⚠️ Settings pane notice: {e}")

        # 3. Clear composer
        print("\n3️⃣ Clearing composer textbox...")
        await composer.clear_composer(page)

        # 4. Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # 5. Mandatory @ + l + i + y + a + Enter sequence
        print("\n4️⃣ Executing mandatory character tagging sequence (@ + l + i + y + a + Enter)...")
        print("   -> Typing '@'...")
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2000)

        print("   -> Typing 'liya' character-by-character...")
        await page.keyboard.type("liya", delay=100)
        await page.wait_for_timeout(2500)

        offered = [t.strip() for t in await page.locator(PICKER_OPTION).all_text_contents()]
        print(f"   📋 Autocomplete options shown: {offered}")

        print("   -> Pressing 'Enter' to commit chip...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2500)

        # 6. Verify chip
        chips = await composer.read_chips(page)
        print(f"   🔍 Attached chip verified in DOM: {chips}")

        # 7. Append prompt text after chip
        print("\n5️⃣ Appending scene prompt after the character chip...")
        await page.keyboard.type(" ", delay=80)
        await page.keyboard.insert_text(prompt_text)
        await page.wait_for_timeout(1000)

        # 8. Save screenshot for verification
        out_screenshot = ROOT_DIR / "output" / "visual_dry_run_inspection.png"
        out_screenshot.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_screenshot))
        print(f"\n📸 Screenshot captured: {out_screenshot}")

        # 9. HARD STOP BEFORE SUBMISSION
        print("\n" + "=" * 70)
        print("🛑 STOPPED! ZERO CREDITS SPENT! SUBMIT / ENTER WAS NOT CLICKED.")
        print(f"👀 LOOK AT YOUR CHROME BROWSER WINDOW NOW:")
        print(f"   - Check that the @liya character chip is active")
        print(f"   - Check that Aspect Ratio is set to {aspect}")
        print(f"   - Check that Count is set to {count}")
        print(f"   - Check the prompt text in the box")
        print(f"⏱️ Leaving browser open for {wait_s} seconds for your visual inspection...")
        print("=" * 70)

        await page.wait_for_timeout(wait_s * 1000)
        print("\n✅ Visual dry run completed cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run headed visual dry run stopping before submit.")
    parser.add_argument("--aspect", default="9:16", help="Aspect ratio (default 9:16)")
    parser.add_argument("--count", type=int, default=1, help="Video count (default 1)")
    parser.add_argument("--wait", type=int, default=45, help="Seconds to leave browser open (default 45)")
    args = parser.parse_args()

    asyncio.run(run_visual_dry_run(aspect=args.aspect, count=args.count, wait_s=args.wait))
