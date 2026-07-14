import asyncio
import os
import json
import time
from notebooklm import NotebookLMClient
from config import TEMP_DIR
from video.footage import fetch_footage as fallback_fetch_footage

def _get_state_path(fmt: int) -> str:
    # Save states to the git-tracked memory folder to persist across serverless VM runs
    return os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")

def _load_state(fmt: int) -> dict:
    path = _get_state_path(fmt)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_state(fmt: int, state: dict):
    path = _get_state_path(fmt)
    try:
        with open(path, "w") as f:
            json.dump(state, f)
    except Exception:
        pass

def _clear_state(fmt: int):
    path = _get_state_path(fmt)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

async def _retry_call(coro_func, *args, retries=5, delay=5, **kwargs):
    """Retries an async call with exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                raise e
            print(f"   [NotebookLM] Warning: Call failed ({e}). Retrying {attempt}/{retries} in {delay}s...")
            await asyncio.sleep(delay)
            delay *= 2

async def _upscale_video(file_path: str):
    """
    Upscale the downloaded 406x720 video to 1080x1920 using FFmpeg.
    This improves visual quality and guarantees compliance with 1080p Reels.
    Designed to run cross-platform (local Mac & Linux/Render.com).
    """
    import subprocess
    
    if not os.path.exists(file_path):
        return
        
    temp_upscaled = file_path.replace(".mp4", "_upscaled.mp4")
    print(f"   [NotebookLM] Upscaling video to 1080x1920 for high-quality Reels...")
    
    # Universal cross-platform software encoder (standard libx264)
    # Using 'ultrafast' preset and CRF 18 to minimize CPU usage and finish in 1-2 seconds on cloud servers
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-vf", "scale=1080:1920:flags=lanczos",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "copy",
        temp_upscaled
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await process.wait()
        
        if process.returncode == 0 and os.path.exists(temp_upscaled):
            os.replace(temp_upscaled, file_path)
            print("   [NotebookLM] Video successfully upscaled to 1080x1920 (Full HD).")
        else:
            print("   [NotebookLM] Warning: FFmpeg upscaling failed.")
    except Exception as e:
        print(f"   [NotebookLM] Warning: Could not upscale video: {e}")

async def _generate_and_download(script_data: dict, fmt: int, resume: bool) -> str:
    """Async worker to interact with NotebookLM API with State Resume & Retry."""
    state = {}
    if resume:
        state = _load_state(fmt)
        if state:
            print(f"   [NotebookLM] Resuming previous generation from state: Notebook={state.get('notebook_id')}, Task={state.get('task_id')}")

    try:
        async with NotebookLMClient.from_storage() as client:
            notebook_id = state.get("notebook_id")
            task_id = state.get("task_id")
            # Reconstruct the absolute path for cross-environment compatibility (Mac -> Linux)
            saved_output_file = state.get("output_file")
            if saved_output_file:
                output_file = os.path.join(os.path.dirname(TEMP_DIR), "memory", os.path.basename(saved_output_file))
            else:
                output_file = None

            # If we aren't resuming or don't have a valid state, start fresh
            if not notebook_id or not task_id:
                print("   [NotebookLM] Starting new video generation workflow...")
                
                # Determine prompt based on format
                if fmt == 1:
                    topic = script_data.get("chosen_topic", "Science and facts")
                    instructions = (
                        f"Act as a highly creative video editor. For this video, invent a unique, engaging visual style and pacing that perfectly matches the subject matter: {topic}. "
                        f"Optimize the layout for vertical 9:16 mobile screens (Shorts/Reels) and ensure the visuals and subtitles are dynamic to retain attention, experimenting freely with mood and artistic direction."
                    )
                elif fmt == 2:
                    instructions = (
                        "Act as a highly creative video editor. For this uploaded story, invent a unique, engaging visual style and pacing that perfectly matches the subject matter. "
                        "Optimize the layout for vertical 9:16 mobile screens (Shorts/Reels) and ensure the visuals and subtitles are dynamic to retain attention, experimenting freely with mood and artistic direction."
                    )
                elif fmt == 3:
                    topic = script_data.get("dilemma_seed", "Moral dilemma")
                    instructions = (
                        f"Act as a highly creative video editor. For this moral dilemma, invent a unique, engaging visual style and pacing that perfectly matches the subject matter: {topic}. "
                        f"Optimize the layout for vertical 9:16 mobile screens (Shorts/Reels) and ensure the visuals and subtitles are dynamic to retain attention, experimenting freely with mood and artistic direction."
                    )
                else:
                    topic = script_data.get("title", "Dark psychology case")
                    instructions = (
                        f"Act as a highly creative video editor. For this dark psychology case, invent a unique, engaging visual style and pacing that perfectly matches the subject matter: {topic}. "
                        f"Optimize the layout for vertical 9:16 mobile screens (Shorts/Reels) and ensure the visuals and subtitles are dynamic to retain attention, experimenting freely with mood and artistic direction."
                    )


                # 1. Create temporary notebook (Retry up to 5 times)
                notebook_name = f"Auto Gen - Format {fmt} - {int(time.time())}"
                print(f"   [NotebookLM] Creating temporary notebook: '{notebook_name}'")
                notebook = await _retry_call(client.notebooks.create, notebook_name)
                notebook_id = notebook.id

                # 2. Upload script text (Retry up to 5 times)
                script_text = script_data.get("script", instructions)
                print("   [NotebookLM] Uploading script text to ground the AI...")
                source = await _retry_call(client.sources.add_text, notebook_id, title="Video Script", content=script_text)

                # Wait for source to index and be ready
                print("   [NotebookLM] Waiting for source to index and be ready...")
                await _retry_call(client.sources.wait_until_ready, notebook_id, source.id)

                # 3. Trigger cinematic video generation with the selected format (Short, Cinematic, or Explainer)
                from notebooklm import VideoFormat
                from notebooklm._artifact.payloads import nest_source_ids, _artifact_client_options
                from notebooklm.rpc.types import ArtifactTypeCode

                # All daily formats are for Reels/Shorts. 
                # Based on raw Network inspection of the `R7cb6c` RPC call, the new vertical "Short" 
                # video format option on Google's backend is represented by value `4`.
                v_format_val = 4
                if fmt == 1:
                    f_name = "Short Facts"
                elif fmt == 2:
                    f_name = "Short Story"
                elif fmt == 3:
                    f_name = "Short Dilemma"
                else:
                    f_name = "Short Psychology"

                print(f"   [NotebookLM] Triggering {f_name} vertical 9:16 video overview generation with instructions: '{instructions}'")

                source_ids = [source.id]
                source_ids_triple = nest_source_ids(source_ids, 2)
                source_ids_double = nest_source_ids(source_ids, 1)

                # Construct the 5-element cinematic video configuration payload (no style code)
                params = [
                    _artifact_client_options(),
                    notebook_id,
                    [
                        None,
                        None,
                        ArtifactTypeCode.VIDEO.value,
                        source_ids_triple,
                        None,
                        None,
                        None,
                        None,
                        [
                            None,
                            None,
                            [
                                source_ids_double,
                                "en",  # language
                                instructions,
                                None,
                                v_format_val,
                            ],
                        ],
                    ],
                ]

                # Make the generate call directly using the client's RPC executor
                status = await _retry_call(
                    client.artifacts._call_generate,
                    notebook_id,
                    params,
                    null_result_artifact_type="cinematic video"
                )
                task_id = status.task_id
                output_file = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"notebooklm_f{fmt}_{int(time.time())}.mp4")


                # Save state immediately so we can resume if we get interrupted during render/download
                _save_state(fmt, {
                    "notebook_id": notebook_id,
                    "task_id": task_id,
                    "output_file": output_file,
                    "script_data": script_data
                })
                print("   [NotebookLM] Task triggered successfully. Exiting to run other formats in parallel.")
                raise Exception("Task rendering in background")

            # 4. Wait for completion (Short 5s poll check to prevent billing actions minutes)
            print(f"   [NotebookLM] Checking task {task_id} status (timeout 5s)...")
            try:
                await client.artifacts.wait_for_completion(notebook_id, task_id, timeout=5.0)
            except Exception as e:
                err_msg = str(e).lower()
                if "timeout" in err_msg or "deadline" in err_msg:
                    raise Exception("Task rendering in background")
                raise e

            # 5. Download the completed video (Retry up to 5 times)
            print(f"   [NotebookLM] Downloading completed video to '{output_file}'...")
            await _retry_call(client.artifacts.download_video, notebook_id, output_file)
            print("   [NotebookLM] Download complete.")

            # 5b. Upscale the video to 1080x1920 (Full HD vertical)
            await _upscale_video(output_file)

            # NOTE: We no longer delete the notebook or the state file here.
            # They will be kept intact so we can re-download if the YouTube upload crashes.
            # `cleanup_notebooklm_state(fmt)` must be called by main.py ONLY after successful upload.

            return output_file

    except Exception as e:
        print(f"   [NotebookLM] Generation pipeline failed: {e}")
        err_msg = str(e).lower()
        # Keep state if it's a timeout/deadline/background render — task is still running.
        # Clear state only on genuine critical failures to prevent infinite retry loops.
        is_still_running = any(kw in err_msg for kw in ["timeout", "timed out", "deadline", "rendering in background"])
        if "not_found" in err_msg:
            is_still_running = False
            
        if not is_still_running:
            print("   [NotebookLM] Critical non-timeout failure (or task not found). Clearing state.")
            _clear_state(fmt)
        raise e


def fetch_notebooklm_footage(script_data: dict, duration_needed: float, fmt: int, resume: bool = False) -> list[str]:
    """
    Synchronous wrapper to fetch NotebookLM cinematic B-roll with state resume and retries.
    """
    print(f"🎬 Requesting AI Cinematic Footage from NotebookLM (Format {fmt}, Resume={resume})...")
    
    # Force resume if a saved state file exists in memory/
    state_file = os.path.join(os.path.dirname(TEMP_DIR), "memory", f"nblm_state_f{fmt}.json")
    if os.path.exists(state_file):
        print(f"   [NotebookLM] Found active state file for Format {fmt}. Forcing resume mode.")
        resume = True

    # Check if a video was already generated and downloaded in memory/ folder
    import glob
    existing_videos = glob.glob(os.path.join(os.path.dirname(TEMP_DIR), "memory", f"notebooklm_f{fmt}_*.mp4"))
    if existing_videos:
        existing_videos.sort(key=os.path.getmtime)
        valid_video = existing_videos[-1]
        if os.path.exists(valid_video) and os.path.getsize(valid_video) > 1024 * 1024:
            print(f"   [NotebookLM] Found existing generated video on disk: {os.path.basename(valid_video)}. Skipping regeneration.")
            try:
                asyncio.run(_upscale_video(valid_video))
            except Exception as ue:
                print(f"   [NotebookLM] Warning: Could not upscale existing video: {ue}")
            return [valid_video]

    try:
        # Run the async generation block
        video_path = asyncio.run(_generate_and_download(script_data, fmt, resume))
        if video_path and os.path.exists(video_path):
            print(f"   ✅ NotebookLM Footage Ready: {os.path.basename(video_path)}")
            return [video_path]
    except Exception as e:
        err_msg = str(e).lower()
        is_still_running = any(kw in err_msg for kw in ["timeout", "timed out", "deadline", "rendering in background"])
        if "not_found" in err_msg:
            is_still_running = False
            
        if is_still_running:
            print(f"   [NotebookLM] Task is still processing: {e}")
            raise e
        print(f"   [NotebookLM] Fatal error in fetch_notebooklm_footage: {e}")
        
    print("   ⚠️ NotebookLM footage generation failed. Falling back to classic gameplay B-roll...")
    return fallback_fetch_footage(
        keyword=script_data.get("pexels_keyword", ""),
        duration_needed=duration_needed,
        fmt=fmt
    )

def cleanup_notebooklm_state(fmt: int):
    """
    Called by main.py ONLY after a successful YouTube upload.
    This safely deletes the notebook from NotebookLM and clears the local state file.
    """
    state = _load_state(fmt)
    notebook_id = state.get("notebook_id")
    if notebook_id:
        print(f"   [NotebookLM] Upload successful! Deleting temporary notebook: {notebook_id}")
        try:
            async def _delete():
                async with NotebookLMClient.from_storage() as client:
                    await client.notebooks.delete(notebook_id)
            asyncio.run(_delete())
        except Exception as e:
            print(f"   [NotebookLM] Warning: Could not delete notebook {notebook_id} on Google's end: {e}")
            
    _clear_state(fmt)
    print(f"   [NotebookLM] Cleared nblm_state_f{fmt}.json")
