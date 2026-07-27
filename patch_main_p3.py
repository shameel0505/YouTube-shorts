import re

with open("main.py", "r") as f:
    code = f.read()

new_p3 = '''            # ── Priority 3: Time-Window Dispatcher
            utc_hour = datetime.now(timezone.utc).hour
            completed_formats = state.get("posted_formats", []) + state.get("exhausted_formats", [])
            
            target_fmt = None
            if "1" not in completed_formats and utc_hour >= 9:
                target_fmt = "1"
            elif "2" not in completed_formats and utc_hour >= 13:
                target_fmt = "2"
            elif "3" not in completed_formats and utc_hour >= 17:
                target_fmt = "3"
            elif "4" not in completed_formats and utc_hour >= 21:
                target_fmt = "4"
                
            status_allows_retry = state["status"] in ("pending", "failed")
            
            if target_fmt and status_allows_retry:
                if can_retry_today(target_fmt):
                    retry_counts = state.get("retry_counts", {})
                    retry_num = retry_counts.get(target_fmt, 0) + 1
                    
                    if state["status"] == "failed":
                        log(f"⚠️ Previous run failed. Retry attempt {retry_num}/3 for Format {target_fmt} today...")
                    else:
                        log(f"⏰ Time window open! Starting fresh pipeline for Format {target_fmt}.")
                    
                    start_fresh_run(target_fmt)
                    notify_pipeline_started(f"Fresh Run (Format {target_fmt})", state["current_day"])
                    try:
                        fmt_list = [target_fmt]
                        results = run_all_formats(upload, niche=args.niche, manual=args.manual, resume=False, mock=args.mock, fmt_list=fmt_list, resume_only=False)
                        
                        is_rendering = any(res.get("rendering") for res in results.values())
                        if is_rendering:
                            set_active_render(True)
                        else:
                            posted_formats_this_run = [fmt_id for fmt_id, res in results.items() if res.get("result", {}).get("url")]
                            if posted_formats_this_run:
                                for pf in posted_formats_this_run:
                                    mark_posted(pf)
                            else:
                                mark_skipped(f"Pipeline finished but Format {target_fmt} was not uploaded.", target_fmt)
                    except Exception as e:
                        import traceback
                        if not can_retry_today(target_fmt):
                            from memory.state_manager import mark_exhausted
                            mark_exhausted(target_fmt, str(e))
                            notify_pipeline_failed(str(e), f"Format {target_fmt} failed 3 times and is permanently skipped for today.")
                        else:
                            mark_failed(str(e))
                            notify_pipeline_failed(str(e), f"Format {target_fmt} failed. Check logs.")
                        log(traceback.format_exc())
                    exit(0)

            # ── No action needed
            if state["status"] == "posted":
                log(f"✅ All formats posted today ({state.get('posted_formats', [])}). Nothing to do.")
            elif state["status"] == "failed":
                log(f"❌ Target format {target_fmt} exhausted its 3 retries. Moving to next window.")
                notify_pipeline_skipped(f"Max retries exhausted for Format {target_fmt}.")
            else:
                log(f"⏭️ No active render or pending run. Status: {state['status']}. Resume check taking no action.")
            exit(0)
        else:'''

# Replace from "# ── Priority 3" until "else:" before "Normal run"
pattern = re.compile(r'            # ── Priority 3: Time-Window Dispatcher\n.*?            exit\(0\)\n        else:', re.DOTALL)
new_code = pattern.sub(new_p3, code)

with open("main.py", "w") as f:
    f.write(new_code)
print("Patched Priority 3 successfully!")
