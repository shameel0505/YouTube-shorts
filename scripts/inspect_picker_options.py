"""
Zero-credit probe to inspect all options offered by Flow's '@' picker in the active project.
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

async def inspect_picker():
    profile_name = _resolve_profile("youtube")
    pdir = _make_provider_dir(profile_name)

    print("=" * 70)
    print("🔍 ZERO-CREDIT PROBE: Inspecting '@' Mention Picker Options in Flow")
    print(f"   Project: {PROJECT_ID}")
    print("=" * 70)

    async with FlowApiClient(profile_dir=pdir, headless=True) as client:
        page = client._pages[0]
        
        # Land on editor
        url = f"https://flow.google.com/u/0/project/{PROJECT_ID}"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_timeout(4000)

        # Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # Clear
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(500)

        # Type @
        print("Typing '@' to trigger mention picker...")
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2500)

        # Inspect all options
        options = await page.locator(PICKER_OPTION).all()
        print(f"\n📋 Found {len(options)} option(s) in the '@' autocomplete picker:\n")

        details = []
        for i, opt in enumerate(options):
            text = (await opt.text_content() or "").strip()
            inner_html = await opt.inner_html()
            attrs = await opt.evaluate("""el => {
                const res = {};
                for (let a of el.attributes) {
                    res[a.name] = a.value;
                }
                const img = el.querySelector('img');
                if (img) res['img_src'] = img.src;
                return res;
            }""")
            print(f"[{i+1}] Text: '{text}' | Attrs: {attrs}")
            details.append({"index": i+1, "text": text, "attrs": attrs})

        # Close picker
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

if __name__ == "__main__":
    asyncio.run(inspect_picker())
