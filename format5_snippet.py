def run_format5(upload: bool = True, attempt: int = 1, resume: bool = False, mock: bool = False, resume_only: bool = False):
    """
    Format 5: Long-Form Cinematic Widescreen Video.
    Generated on a 2-day schedule.
    """
    from generator.script import generate_long_video
    from video.notebooklm_footage import fetch_notebooklm_footage
    from uploader.youtube import upload_video
    fmt = 5
    state_path = os.path.join(TEMP_DIR, "memory", f"nblm_state_f{fmt}.json")
    result = {}

    if attempt > 1:
        log(f"⚠️  Retrying Format 5 (Attempt {attempt}/3)...", fmt)
        time.sleep(10)
    else:
        log(f"━━━━━━━━━━━━━━━━━━ FORMAT 5: LONG-FORM VIDEO ━━━━━━━━━━━━━━━━━━", fmt)

    if not quota_tracker.can_proceed(2) and not (resume_only and os.path.exists(state_path)):
        log("⏭️  Quota exhausted. Skipping Format 5.", fmt)
        return {"format": 5, "skipped": True}

    log(f"🚀 Starting Long-Form Video | upload: {upload} | attempt: {attempt}", fmt)

    if attempt == 1 and not resume:
        _clean_temp_for_format(5)

    script_path  = os.path.join(TEMP_DIR, "script_f5.json")

    try:
        if resume_only and os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    saved_state = json.load(f)
                script_data = saved_state.get("script_data") or {}
                log("⏩ Resume mode: Skipping research. Checking NotebookLM render status...", fmt)
            except Exception:
                script_data = {}
        else:
            script_data = None
            if os.path.exists(script_path):
                with open(script_path) as f:
                    cached_data = json.load(f)
                from memory.content_log import is_topic_used
                if is_topic_used(cached_data.get("used_topic_seed", cached_data.get("title", "")), 5):
                    log("♻️  Cached script is stale (already uploaded previously). Wiping temp to recreate...", fmt)
                    _clean_temp_for_format(5)
                else:
                    log("📝 Loading cached script...", fmt)
                    script_data = cached_data

            if not script_data:
                if mock:
                    log("🧪 Dry run: Mock script", fmt)
                    script_data = {
                        "topic": "Mock", "title": "Mock", "description": "Mock", "hashtags": ["#mock"], "script": "Mock", "notebooklm_instructions": "Mock"
                    }
                else:
                    if not quota_tracker.can_proceed(2):
                        raise RuntimeError("Gemini quota exhausted.")
                    log("📝 Step 1 & 2: Generating long-form script...", fmt)
                    script_data = generate_long_video()
                    log(f"   Title: {script_data['title']}", fmt)
                    log(f"   {quota_tracker.status()}", fmt)

                with open(script_path, "w") as f:
                    json.dump(script_data, f)

        log("🎬 Step 4: Generating NotebookLM 16:9 video...", fmt)
        footage_paths = fetch_notebooklm_footage(
            script_data=script_data,
            duration_needed=180.0,
            fmt=5,
            resume=resume or resume_only
        )
        video_path = footage_paths[0]
        log(f"   ✅ Saved: {video_path}", fmt)

        if upload:
            log("📤 Step 7: Uploading to YouTube...", fmt)
            result = upload_video(
                video_path, script_data["title"],
                script_data["description"], script_data["hashtags"],
                is_short=False
            )
            log(f"   ✅ YouTube Live: {result['url']}", fmt)
            
            from analytics.tracker import log_upload
            from memory.content_log import add_used_topic
            if "video_id" in result:
                log_upload(result["video_id"], 5, script_data["title"], script_data.get("hook", ""))
            add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 5)
        else:
            log("⏭️  Upload skipped (dry run)", fmt)
            result = {"video_path": video_path}

        from video.notebooklm_footage import cleanup_notebooklm_state
        cleanup_notebooklm_state(5)

        log("🎉 Format 5 completed successfully!", fmt)
        return {"format": 5, "script": script_data, "video_path": video_path, "result": result}

    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "deadline" in err_msg or "rendering in background" in err_msg:
            log(f"⏳ NotebookLM video generation is still processing. Saving state. The next run will resume.", fmt)
            return {"format": 5, "rendering": True, "script": locals().get("script_data")}
        log(f"❌ Format 5 failed: {e}", fmt)
        log(traceback.format_exc(), fmt)
        raise

