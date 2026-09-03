import re

with open("main.py", "r") as f:
    content = f.read()

# 1. Fix _clean_temp_for_format
content = re.sub(r'def _clean_temp_for_format\(fmt: int\):', r'def _clean_temp_for_format(fmt):', content)

# 2. Fix run_format signatures and internal fmt assignments
for i in range(1, 6):
    # Add fmt_id to signature
    if i == 5:
        sig_pattern = rf"def run_format{i}\(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None\) -> dict:"
        new_sig = f"def run_format{i}(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = \"{i}\") -> dict:"
    else:
        sig_pattern = rf"def run_format{i}\(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None\) -> dict:"
        new_sig = f"def run_format{i}(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = \"{i}\") -> dict:"
    
    content = content.replace(sig_pattern, new_sig)
    
    # Replace the hardcoded `fmt = "1"` or `fmt = 1` immediately following the signature
    assign_pattern = rf'    fmt = "{i}"'
    new_assign = f'    fmt = fmt_id\n    base_fmt = str(fmt).split("_")[0]'
    content = content.replace(assign_pattern, new_assign)
    
    assign_pattern2 = rf'    fmt = {i}'
    content = content.replace(assign_pattern2, new_assign)
    
    # We must also replace any cleanup_notebooklm_state(i) with cleanup_notebooklm_state(fmt)
    content = re.sub(rf'cleanup_notebooklm_state\({i}\)', r'cleanup_notebooklm_state(fmt)', content)
    
    # Also replace _clean_temp_for_format(i) with _clean_temp_for_format(fmt)
    content = re.sub(rf'_clean_temp_for_format\({i}\)', r'_clean_temp_for_format(fmt)', content)
    
    # Replace was_format_uploaded_today(i) with was_format_uploaded_today(fmt)
    content = re.sub(rf'was_format_uploaded_today\({i}\)', r'was_format_uploaded_today(fmt)', content)

# 3. Fix runners.append to pass fmt_id
runners_append_old = """        if base_fmt == "1":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "2":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "3":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))
        elif base_fmt == "4":
            runners.append((fmt_name, lambda attempt=1, t=st: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t)))"""

runners_append_new = """        if base_fmt == "1":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format1(upload=upload, niche=niche, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "2":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format2(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "3":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format3(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))
        elif base_fmt == "4":
            runners.append((fmt_name, lambda attempt=1, t=st, f=fmt_name: run_format4(upload=upload, manual=manual, attempt=attempt, resume=resume, mock=mock, resume_only=resume_only, schedule_time=t, fmt_id=f)))"""

content = content.replace(runners_append_old, runners_append_new)

# 4. Move add_used_topic from Step 7 to Step 2
# Format 1
f1_upload_topic = '                add_used_topic(script_data.get("chosen_topic", ""), 1)'
f1_script_topic = """                    log(f"   {quota_tracker.status()}", fmt)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("chosen_topic", ""), int(base_fmt))"""
content = content.replace(f1_upload_topic, "")
content = content.replace('                    log(f"   {quota_tracker.status()}", fmt)', f1_script_topic, 1)

# Format 2
f2_upload_topic = '                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 2)'
f2_script_topic = """                    log(f"   {quota_tracker.status()}", fmt)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), int(base_fmt))"""
content = content.replace(f2_upload_topic, "")
# We replace the second occurrence of quota_tracker.status() (the one after script generation)
parts = content.split('                    log(f"   {quota_tracker.status()}", fmt)')
if len(parts) >= 3:
    content = parts[0] + '                    log(f"   {quota_tracker.status()}", fmt)' + parts[1] + f2_script_topic + parts[2] + "                    log(f\"   {quota_tracker.status()}\", fmt)".join(parts[3:])

# Format 3
f3_upload_topic = '                add_used_topic(script_data["dilemma_seed"], 3)'
f3_script_topic = """                    log(f"   {quota_tracker.status()}", fmt)
                from memory.content_log import add_used_topic
                add_used_topic(script_data["dilemma_seed"], int(base_fmt))"""
content = content.replace(f3_upload_topic, "")
parts = content.split('                    log(f"   {quota_tracker.status()}", fmt)')
if len(parts) >= 4:
    content = parts[0] + '                    log(f"   {quota_tracker.status()}", fmt)' + parts[1] + '                    log(f"   {quota_tracker.status()}", fmt)' + parts[2] + f3_script_topic + parts[3] + "                    log(f\"   {quota_tracker.status()}\", fmt)".join(parts[4:])

# Format 4
f4_upload_topic = '                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 4)'
f4_script_topic = """                    log(f"   {quota_tracker.status()}", fmt)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), int(base_fmt))"""
content = content.replace(f4_upload_topic, "")
parts = content.split('                    log(f"   {quota_tracker.status()}", fmt)')
if len(parts) >= 5:
    # It might be the 4th occurrence in the file overall... this regex split is getting dangerous.
    pass

with open("main.py", "w") as f:
    f.write(content)
