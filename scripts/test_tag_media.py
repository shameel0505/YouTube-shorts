"""
Test tagging a media asset in Google Flow composer using:
@ + "Host speaking at wooden desk" + Enter
Zero credits spent: halts before clicking submit and captures a screenshot.
"""
import sys
import os
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from gflow_cli.api.client import FlowApiClient
from gflow_cli._cli_helpers import _resolve_profile, _make_provider_dir
from gflow_cli.api.transports.migrated_composer import (
    COMPOSER,
    PICKER_OPTION,
)

PROJECT_ID = os.environ.get("FLOW_PROJECT_ID", "f8d0e960-846a-42d6-a643-333562c0d44f")
TARGET_QUERY = sys.argv[1] if len(sys.argv) > 1 else "Scene 02"

async def test_tag_media():
    profile_name = _resolve_profile("youtube")
    pdir = _make_provider_dir(profile_name)

    print("=" * 70)
    print(f"🎬 ZERO-CREDIT PROBE: Testing '@ + {TARGET_QUERY} + Enter'")
    print(f"   Project: {PROJECT_ID}")
    print("=" * 70)

    async with FlowApiClient(profile_dir=pdir, headless=False) as client:
        page = client._pages[0]
        
        # 1. Navigate to editor
        url = f"https://flow.google.com/u/0/project/{PROJECT_ID}"
        print(f"1️⃣ Navigating to Flow editor: {url}")
        await page.goto(url)
        await page.wait_for_timeout(4000)

        # 2. Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # 3. Clear existing text/chips
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(500)

        # 4. Type '@'
        print("2️⃣ Typing '@' to open mention picker...")
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2000)

        # 5. Type query if specified
        if TARGET_QUERY and TARGET_QUERY.lower() not in ("all", "none", ""):
            print(f"3️⃣ Typing '{TARGET_QUERY}' character by character...")
            await page.keyboard.type(TARGET_QUERY, delay=60)
            await page.wait_for_timeout(2500)
        else:
            print("3️⃣ No filter typed; waiting for default options list...")
            await page.wait_for_timeout(2500)

        # 6. Read filtered options
        options = await page.locator(PICKER_OPTION).all()
        print(f"📋 Filtered options found: {len(options)}")
        option_texts = []
        for i, opt in enumerate(options):
            t = (await opt.text_content() or "").strip()
            print(f"   Option [{i}]: '{t}'")
            option_texts.append(t)

        if not options:
            print("❌ No matching options found in autocomplete dropdown.")
            return

        # 7. Select specifically the Video option if present, else first option
        target_idx = 0
        for i, t in enumerate(option_texts):
            if t.endswith("Video"):
                target_idx = i
                print(f"🎯 Target video option found at index [{i}]: '{t}'")
                break

        print(f"4️⃣ Navigating to option [{target_idx}] and pressing 'Enter' to commit...")
        for _ in range(target_idx):
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(200)

        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2500)

        # 8. Inspect chips in DOM
        chips = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('.mention-chip, [data-reference-type], button.chip-container, mat-chip'));
            return els.map(e => ({
                tag: e.tagName,
                text: e.textContent.trim(),
                reference_type: e.getAttribute('data-reference-type'),
                entity_id: e.getAttribute('entity_id') || e.getAttribute('data-entity-id'),
                media_id: e.getAttribute('data-media-id') || e.getAttribute('media_id'),
                attrs: Array.from(e.attributes).reduce((acc, a) => { acc[a.name] = a.value; return acc; }, {})
            }));
        }''')

        print(f"\n🔍 Chips detected in DOM: {len(chips)}")
        for i, c in enumerate(chips):
            print(f"   Chip [{i}]: text='{c['text']}', type='{c['reference_type']}', attrs={c['attrs']}")

        # 9. Screenshot for visual inspection
        out_png = ROOT_DIR / "output" / "test_tag_media_inspection.png"
        out_png.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_png))
        print(f"\n📸 Screenshot captured: {out_png}")

        # 8. Type space and then tag @liya character chip
        print("\n5️⃣ Appending '@liya' character chip after the previous video chip...")
        await page.keyboard.type(" ", delay=80)
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2000)
        print("   -> Typing 'liya' character by character...")
        for ch in "liya":
            await page.keyboard.type(ch, delay=100)
        await page.wait_for_timeout(2500)
        print("   -> Pressing 'Enter' to commit @liya chip...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2500)

        # 9. Type space and append script prompt
        print("\n6️⃣ Appending full script prompt after both chips...")
        await page.keyboard.type(" ", delay=80)
        prompt_text = (
            "Full-frame 9:16 image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens, "
            "medium waist-up shot at minimalist timber creator studio desk, host wearing the tailored matte charcoal overshirt "
            "over crisp crewneck with generous headroom, authentic natural skin texture with visible micro-pores, illuminated by "
            "warm 3200K softbox key light at 45 degrees with subtle warm rim accent, organic optical bokeh. The shot opens with the "
            "host looking directly into the camera lens with engaging warmth and closed mouth in a brief 0.5-second natural resting "
            "pause, takes a subtle breath, and then begins speaking with relaxed conviction saying: \"Electricity needs free-moving ions "
            "to carry a current through the liquid medium.\", using subtle natural hand gestures, and as the words finish, pauses "
            "naturally with a subtle knowing nod and rests hands easily on the timber desk, keeping warm direct eye contact with the "
            "viewer with zero frozen stillness or awkward sideways glances, sharp cinematic 4k."
        )
        await page.keyboard.insert_text(prompt_text)
        await page.wait_for_timeout(1500)

        # 10. Inspect all chips in DOM
        chips = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('.mention-chip, [data-reference-type], button.chip-container, mat-chip'));
            return els.map(e => ({
                tag: e.tagName,
                text: e.textContent.trim(),
                reference_type: e.getAttribute('data-reference-type'),
                entity_id: e.getAttribute('entity_id') || e.getAttribute('data-entity-id'),
                media_id: e.getAttribute('data-media-id') || e.getAttribute('media_id'),
                attrs: Array.from(e.attributes).reduce((acc, a) => { acc[a.name] = a.value; return acc; }, {})
            }));
        }''')

        print(f"\n🔍 Chips detected in DOM: {len(chips)}")
        for i, c in enumerate(chips):
            print(f"   Chip [{i}]: text='{c['text']}', type='{c['reference_type']}', entity_id='{c['entity_id']}', media_id='{c['media_id']}'")

        # 11. Screenshot for visual inspection
        out_png = ROOT_DIR / "output" / "test_tag_video_and_liya_continuation.png"
        out_png.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_png))
        print(f"\n📸 Screenshot captured: {out_png}")

        # 12. Read composer inner HTML / text
        composer_html = await comp.inner_html()
        print(f"\n📝 Composer Content (sanitized):\n{composer_html[:400]}...")

        print("\n" + "=" * 70)
        print("🛑 STOPPED BEFORE SUBMIT! ZERO CREDITS SPENT.")
        print("👀 CHECK YOUR SCREEN: Both previous video AND @liya are tagged together!")
        print("=" * 70)
        await page.wait_for_timeout(5000)

if __name__ == "__main__":
    asyncio.run(test_tag_media())
