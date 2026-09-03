with open("main.py", "r") as f:
    text = f.read()

text = text.replace("def _clean_temp_for_format(fmt: int):", "def _clean_temp_for_format(fmt):")

for i in range(1, 6):
    text = text.replace(f"was_format_uploaded_today({i})", "was_format_uploaded_today(fmt)")
    text = text.replace(f"_clean_temp_for_format({i})", "_clean_temp_for_format(fmt)")
    text = text.replace(f"cleanup_notebooklm_state({i})", "cleanup_notebooklm_state(fmt)")

s1_old = 'def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None) -> dict:\n    fmt = "1"'
s1_new = 'def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "1") -> dict:\n    fmt = fmt_id\n    base_fmt = str(fmt).split("_")[0]'
text = text.replace(s1_old, s1_new)

for i in [2, 3, 4]:
    s_old = f'def run_format{i}(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None) -> dict:\n    fmt = "{i}"'
    s_new = f'def run_format{i}(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = "{i}") -> dict:\n    fmt = fmt_id\n    base_fmt = str(fmt).split("_")[0]'
    text = text.replace(s_old, s_new)

# runners.append
runners_old = """        if base_fmt == "1":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "2":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "3":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "4":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))"""

runners_new = """        if base_fmt == "1":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "2":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "3":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "4":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))"""

text = text.replace(runners_old, runners_new)

# EXACT string replacements for adding used topic
t1_old = '                with open(script_path, "w") as f:\n                    json.dump(script_data, f)'
t1_new = '                with open(script_path, "w") as f:\n                    json.dump(script_data, f)\n                from memory.content_log import add_used_topic\n                add_used_topic(script_data.get("chosen_topic", ""), int(base_fmt))'
t2_new = '                with open(script_path, "w") as f:\n                    json.dump(script_data, f)\n                from memory.content_log import add_used_topic\n                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), int(base_fmt))'
t3_new = '                with open(script_path, "w") as f:\n                    json.dump(script_data, f)\n                from memory.content_log import add_used_topic\n                add_used_topic(script_data["dilemma_seed"], int(base_fmt))'

# Since we want to replace them in order (f1, f2, f3, f4), we can just replace the first occurrence 4 times!
text = text.replace(t1_old, t1_new, 1) # Format 1
text = text.replace(t1_old, t2_new, 1) # Format 2
text = text.replace(t1_old, t3_new, 1) # Format 3
text = text.replace(t1_old, t2_new, 1) # Format 4 (same as 2)

# Remove the old upload ones
text = text.replace('                add_used_topic(script_data.get("chosen_topic", ""), 1)\n', '')
text = text.replace('                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 2)\n', '')
text = text.replace('                add_used_topic(script_data["dilemma_seed"], 3)\n', '')
text = text.replace('                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 4)\n', '')

# Telegram spam patch
spam_old = """                if res.get("rendering"):
                    title = res.get('script', {}).get('title', 'Unknown')
                    try:
                        from telegram.approver import notify_pipeline_running
                        notify_pipeline_running(fmt_name, title)
                    except: pass
                    break"""
spam_new = """                if res.get("rendering"):
                    title = res.get('script', {}).get('title', 'Unknown')
                    if not resume_only:
                        try:
                            from telegram.approver import notify_pipeline_running
                            notify_pipeline_running(fmt_name, title)
                        except: pass
                    break"""
text = text.replace(spam_old, spam_new)

with open("main.py", "w") as f:
    f.write(text)
