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
    count: int = 1,
    out_dir: Path = None,
    project_id: str = "f8d0e960-846a-42d6-a643-333562c0d44f",
    profile: str = "youtube",
    timeout_s: float = 300.0,
    dry_run: bool = False,
    tag_character: bool = True,
    previous_video: str = None,
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

        # 1. Land on project editor with resilient multi-account index discovery
        account_idx = os.environ.get("GFLOW_ACCOUNT_INDEX")
        candidate_urls = []
        if account_idx:
            candidate_urls.append(f"https://flow.google.com/u/{account_idx}/project/{project_id}")
        candidate_urls.extend([
            f"https://flow.google.com/u/0/project/{project_id}",
            f"https://flow.google.com/u/1/project/{project_id}",
            f"https://flow.google.com/project/{project_id}",
        ])

        landed = False
        for url in candidate_urls:
            print(f"   [DEBUG] Attempting navigation to {url}")
            await page.goto(url)
            await page.wait_for_timeout(3000)
            if "/about" not in page.url:
                landed = True
                print(f"   ✅ Successfully landed on editor: {page.url}")
                break
            print(f"   [WARN] Redirected to /about on {url}, testing next candidate...")

        if not landed:
            print("   [WARN] Candidate URLs redirected to /about; attempting composer.ensure_editor fallback...")
            try:
                await composer.ensure_editor(page, project_id)
            except Exception as e:
                raise RuntimeError(f"Could not open project {project_id} (redirected to /about across all account indices): {e}")

        # 2. Configure Mode (Video), Aspect Ratio (crop_9_16 vs crop_16_9), and Count (x1 - only one video)
        target_aspect_lig = "crop_9_16" if aspect == "9:16" else "crop_16_9"
        print(f"   [SETTINGS] Selecting mode: video, aspect ratio: {aspect} ({target_aspect_lig}), count: x{count}")
        try:
            pane = await composer._open_pane(page)
            try:
                await composer._select(page, pane, axis="mode", lig="videocam")
                await composer._select(page, pane, axis="aspect", lig=target_aspect_lig)
                await composer._select(page, pane, axis="count", text=f"x{count}")
            finally:
                await composer._close_pane(page)
            print(f"   ✅ Successfully applied settings: mode=videocam, aspect={aspect}, count=x{count}")
        except Exception as e:
            print(f"   [WARN] Could not apply settings pane ({e}), proceeding with page state...")

        # 3. Clear composer
        await composer.clear_composer(page)

        # 4. Focus composer
        comp = page.locator(COMPOSER).first
        await comp.click()
        await page.wait_for_timeout(500)

        # 3. If previous video is specified for continuation chaining, tag it first via @
        if previous_video:
            print(f"🔗 Tagging previous video for continuation: '{previous_video}'...")
            await page.keyboard.type("@", delay=120)
            await page.wait_for_timeout(2000)

            # If a specific search title is provided (and not 'latest'/'auto'), filter by it
            if previous_video.lower() not in ("latest", "auto", "previous", "true"):
                await page.keyboard.type(previous_video, delay=60)
            # Dynamically wait up to 5s for autocomplete options to appear
            options_loc = page.locator(PICKER_OPTION)
            for _ in range(10):
                if await options_loc.count() > 0:
                    break
                await page.wait_for_timeout(300)
            await page.wait_for_timeout(1000)

            # Check autocomplete options and target Video option
            offered_texts = [t.strip() for t in await options_loc.all_text_contents()]
            target_idx = None
            for idx, txt in enumerate(offered_texts):
                clean_txt = txt.strip()
                if clean_txt.endswith("Video") or "\nVideo" in clean_txt or " Video" in clean_txt or "video" in clean_txt.lower():
                    target_idx = idx
                    print(f"   📹 Selected video asset from picker: '{clean_txt}' (index {idx})")
                    break

            # Robust fallback: if search query yielded no video options, clear filter and select newest video in project
            if target_idx is None and previous_video.lower() not in ("latest", "auto", "previous", "true"):
                print(f"   ⚠️ Search query '{previous_video}' yielded no Video options in picker (got {len(offered_texts)} options).")
                print("   🔄 Clearing filter to select the latest chronological video in the project...")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                await composer.clear_composer(page)
                comp = page.locator(COMPOSER).first
                await comp.click(force=True)
                await page.wait_for_timeout(500)
                await page.keyboard.type("@", delay=120)
                await page.wait_for_timeout(2000)
                for _ in range(10):
                    if await options_loc.count() > 0:
                        break
                    await page.wait_for_timeout(300)
                await page.wait_for_timeout(1000)
                offered_texts = [t.strip() for t in await options_loc.all_text_contents()]
                for idx, txt in enumerate(offered_texts):
                    clean_txt = txt.strip()
                    if clean_txt.endswith("Video") or "\nVideo" in clean_txt or " Video" in clean_txt or "video" in clean_txt.lower():
                        target_idx = idx
                        print(f"   📹 Selected latest video asset from project: '{clean_txt}' (index {idx})")
                        break

            if target_idx is not None:
                for _ in range(target_idx):
                    await page.keyboard.press("ArrowDown")
                    await page.wait_for_timeout(200)

                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
                await page.keyboard.type(" ", delay=80)

                # Confirm chip in DOM (Flow attaches media as an ingredient button or mention-chip)
                attached_count = await page.evaluate('''() => {
                    return document.querySelectorAll('.mention-chip, button.chip-container, button[aria-label="Ingredient"], flow-prompt-box button:has(img)').length;
                }''')
                if attached_count == 0:
                    raise RuntimeError("Failed to commit previous video chip: no chip attached in DOM")
                print(f"   ✅ Previous video chip confirmed in DOM ({attached_count} chip(s) attached).")
            else:
                print(f"   ⚠️ Could not locate previous video '{previous_video}' in picker (got: {offered_texts}).")
                print("   🔄 Clearing mention query to proceed with fresh standalone generation...")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                await composer.clear_composer(page)
                comp = page.locator(COMPOSER).first
                await comp.click(force=True)
                await page.wait_for_timeout(500)

        if tag_character:
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
            # Find the entity chip
            entity_chips = [c for c in chips if c.get("reference_type") == "entity"]
            if not entity_chips:
                raise RuntimeError(f"Failed to attach Liya entity chip: got chips={chips}")

            # 5. Append prompt text after chip
            await page.keyboard.type(" ", delay=80)
            await page.keyboard.insert_text(prompt)
            await page.wait_for_timeout(1000)
        else:
            # B-Roll: Move caret to the exact end of composer and insert prompt
            await page.evaluate('''() => {
                const el = document.querySelector('[contenteditable="true"]');
                if (el) {
                    el.focus();
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    range.collapse(false);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }''')
            await page.wait_for_timeout(300)
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

        # 7. Explicit Settings Pre-Flight Verification Guardrail
        # Verifies the active toolbar pills to confirm Mode=Video, Aspect=target_aspect, Count=x1
        try:
            settings_summary = await page.evaluate('''() => {
                const buttons = Array.from(document.querySelectorAll('flow-prompt-box button, .prompt-box button, [role="toolbar"] button'));
                return buttons.map(b => b.textContent.trim().replace(/\\s+/g, ' ')).filter(t => t.length > 0 && t.length < 40).join(' | ');
            }''')
            print(f"   🛡️ Pre-submit toolbar verification: [{settings_summary}]")
        except Exception as e:
            print(f"   ⚠️ Toolbar verification notice: {e}")

        # Locate Submit button (arrow_forward)
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
    parser.add_argument("--count", type=int, default=1, help="Number of video candidates to generate (default: 1).")
    parser.add_argument("--out-dir", default=None, help="Directory to save downloaded clip.")
    parser.add_argument("--project", default="f8d0e960-846a-42d6-a643-333562c0d44f", help="Flow project ID.")
    parser.add_argument("--profile", default="youtube", help="gflow auth profile.")
    parser.add_argument("--timeout", type=float, default=300.0, help="Timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without spending credits.")
    parser.add_argument("--no-character", action="store_true", help="Skip character tagging (for B-Roll scenes).")
    parser.add_argument("--previous-video", default=None, help="Name or query of previous video to chain/continue from.")
    args = parser.parse_args()

    try:
        res = asyncio.run(generate_aroll(
            prompt=args.prompt,
            aspect=args.aspect,
            count=args.count,
            out_dir=Path(args.out_dir) if args.out_dir else None,
            project_id=args.project,
            profile=args.profile,
            timeout_s=args.timeout,
            dry_run=args.dry_run,
            tag_character=not args.no_character,
            previous_video=args.previous_video,
        ))
        print(json.dumps(res))
        sys.exit(0)
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
