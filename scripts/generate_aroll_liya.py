"""
========================================================================================
🛑 CRITICAL AGENT & AI INSTRUCTION - DO NOT MODIFY WITHOUT EXPLICIT USER APPROVAL 🛑
========================================================================================
Verified A-Roll Character Generator for @liya on flow.google.com.
Follows the exact golden keystroke sequence:
  1. Focus composer
  2. Type '@' (120ms delay) -> wait 2.0s
  3. Type 'liya' (100ms delay) -> wait 2.5s
  4. Press 'Enter' -> commits chip with data-reference-type="entity"
  5. Append scene prompt after chip
  6. Click Submit (arrow_forward)
  7. Observe generation completion via batchexecute & download MP4
========================================================================================
"""
import sys
import os
import json
import time
import asyncio
import argparse
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
    _ligature,
)
from gflow_cli.api.transports.batchexecute import (
    parse_frames,
    generation_record,
    GenerationRecord,
    STATUS_DONE,
)

async def generate_aroll(
    prompt: str,
    aspect: str = "9:16",
    out_dir: Path = None,
    project_id: str = "f8d0e960-846a-42d6-a643-333562c0d44f",
    profile: str = "youtube",
    timeout_s: float = 300.0,
    dry_run: bool = False,
) -> dict:
    out_path = Path(out_dir) if out_dir else (ROOT_DIR / "temp" / "studio" / "clips")
    out_path.mkdir(parents=True, exist_ok=True)

    if dry_run:
        mock_file = out_path / f"mock_liya_aroll_{int(time.time())}.mp4"
        mock_file.write_bytes(b"\x00" * 1024)
        return {"status": "success", "path": str(mock_file), "dry_run": True}

    profile_name = _resolve_profile(profile)
    pdir = _make_provider_dir(profile_name)

    async with FlowApiClient(profile_dir=pdir, headless=False) as client:
        page = client._pages[0]
        composer = MigratedComposer()

        # 1. Land on project editor explicitly using /u/0/ since this is a fresh profile with 1 account
        url = f"https://flow.google.com/u/0/project/{project_id}"
        print(f"   [DEBUG] Forcing navigation to {url}")
        await page.goto(url)
        await page.wait_for_timeout(3000)
        # Verify we didn't get redirected
        if "/about" in page.url:
            raise RuntimeError(f"Still redirected to /about even after forcing {url}. Please check session.")

        # 2. Clear composer
        await composer.clear_composer(page)

        # 3. Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # 4. Mandatory @ + l + i + y + a + Enter sequence
        await page.keyboard.type("@", delay=120)
        await page.wait_for_timeout(2000)
        await page.keyboard.type("liya", delay=100)
        await page.wait_for_timeout(2500)

        # Confirm dropdown has options
        offered = [t.strip() for t in await page.locator(PICKER_OPTION).all_text_contents()]
        if not offered:
            raise RuntimeError(f"Flow mention dropdown did not show any options for 'liya'")

        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2500)

        chips = await composer.read_chips(page)
        if not chips or chips[0].get("reference_type") != "entity":
            raise RuntimeError(f"Failed to attach Liya entity chip: got chips={chips}")

        # 5. Append prompt text after chip
        await page.keyboard.type(" ", delay=80)
        await page.keyboard.insert_text(prompt)
        await page.wait_for_timeout(1000)

        # 6. Prepare completion future
        loop = asyncio.get_running_loop()
        completed_record: asyncio.Future[GenerationRecord] = loop.create_future()
        active_workflow_id: list[str] = []

        def on_response(response):
            if "batchexecute" not in response.url or completed_record.done():
                return
            async def parse_body():
                try:
                    text = await response.text()
                    for rid, payload in parse_frames(text):
                        if payload is None:
                            continue
                        try:
                            rec = generation_record(rid, payload)
                            if rec.workflow_id and not active_workflow_id:
                                active_workflow_id.append(rec.workflow_id)
                            if active_workflow_id and rec.workflow_id != active_workflow_id[0]:
                                continue
                            if rec.is_done and rec.video_url and not completed_record.done():
                                completed_record.set_result(rec)
                        except Exception:
                            pass
                except Exception:
                    pass
            asyncio.create_task(parse_body())

        page.on("response", on_response)

        # 7. Locate Submit button (arrow_forward)
        submit = page.locator("button").filter(has=_ligature(page, "arrow_forward")).first
        if not await submit.count():
            raise RuntimeError("Submit button (arrow_forward) not found in Flow composer")

        # Wait until enabled
        deadline = time.time() + 30
        while not await submit.is_enabled():
            if time.time() > deadline:
                raise RuntimeError("Submit button stayed disabled after typing prompt")
            await asyncio.sleep(0.5)

        # 8. Click Submit
        await submit.click()

        # 9. Wait for generation to complete
        try:
            record = await asyncio.wait_for(completed_record, timeout=timeout_s)
        except asyncio.TimeoutError:
            page.remove_listener("response", on_response)
            raise TimeoutError(f"Video generation timed out after {timeout_s}s")
        finally:
            page.remove_listener("response", on_response)

        # 10. Download finished clip
        downloaded_path = await composer.download(page, record, out_path)
        if not downloaded_path or not downloaded_path.exists():
            raise RuntimeError(f"Download failed for media {record.media_id}")

        return {
            "status": "success",
            "path": str(downloaded_path),
            "media_id": record.media_id,
            "bytes": record.size_bytes,
        }

def main():
    parser = argparse.ArgumentParser(description="Generate A-Roll scene with tagged @liya character.")
    parser.add_argument("--prompt", required=True, help="Scene prompt to append after @liya chip.")
    parser.add_argument("--aspect", default="9:16", help="Aspect ratio (default 9:16).")
    parser.add_argument("--out-dir", default=None, help="Directory to save downloaded clip.")
    parser.add_argument("--project", default="f8d0e960-846a-42d6-a643-333562c0d44f", help="Flow project ID.")
    parser.add_argument("--profile", default="youtube", help="gflow auth profile.")
    parser.add_argument("--timeout", type=float, default=300.0, help="Timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without spending credits.")
    args = parser.parse_args()

    try:
        res = asyncio.run(generate_aroll(
            prompt=args.prompt,
            aspect=args.aspect,
            out_dir=Path(args.out_dir) if args.out_dir else None,
            project_id=args.project,
            profile=args.profile,
            timeout_s=args.timeout,
            dry_run=args.dry_run,
        ))
        print(json.dumps(res))
        sys.exit(0)
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
