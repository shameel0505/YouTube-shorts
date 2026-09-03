with open("main.py", "r") as f:
    text = f.read()

# 1. Update _clean_temp_for_format and was_format_uploaded_today
text = text.replace("def _clean_temp_for_format(fmt: int):", "def _clean_temp_for_format(fmt):")

for i in range(1, 6):
    text = text.replace(f"was_format_uploaded_today({i})", "was_format_uploaded_today(fmt)")
    text = text.replace(f"_clean_temp_for_format({i})", "_clean_temp_for_format(fmt)")
    text = text.replace(f"cleanup_notebooklm_state({i})", "cleanup_notebooklm_state(fmt)")

# 2. Add fmt_id to run_format signatures
text = text.replace(
    "def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None) -> dict:",
    "def run_format1(upload: bool = True, niche: str = None, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = \"1\") -> dict:"
)
for i in [2, 3, 4]:
    text = text.replace(
        f"def run_format{i}(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None) -> dict:",
        f"def run_format{i}(upload: bool = True, attempt: int = 1, manual: bool = False, resume: bool = False, mock: bool = False, resume_only: bool = False, schedule_time=None, fmt_id: str = \"{i}\") -> dict:"
    )

# 3. Fix fmt assignments inside run_formatX
for i in range(1, 5):
    text = text.replace(
        f'    fmt = "{i}"',
        f'    fmt = fmt_id\n    base_fmt = str(fmt).split("_")[0]'
    )

# 4. Fix runners.append
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

# 5. Move add_used_topic for each format to step 2

# F1
f1_upload = '                add_used_topic(script_data.get("chosen_topic", ""), 1)'
f1_script = '''                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("chosen_topic", ""), int(base_fmt))'''
text = text.replace(f1_upload, '')
text = text.replace('                with open(script_path, "w") as f:\n                    json.dump(script_data, f)', f1_script)

# F2
f2_upload = '                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 2)'
f2_script = '''                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), int(base_fmt))'''
text = text.replace(f2_upload, '')
text = text.replace('                with open(script_path, "w") as f:\n                    json.dump(script_data, f)', f2_script)

# F3
f3_upload = '                add_used_topic(script_data["dilemma_seed"], 3)'
f3_script = '''                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data["dilemma_seed"], int(base_fmt))'''
text = text.replace(f3_upload, '')
text = text.replace('                with open(script_path, "w") as f:\n                    json.dump(script_data, f)', f3_script)

# F4
f4_upload = '                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), 4)'
f4_script = '''                with open(script_path, "w") as f:
                    json.dump(script_data, f)
                from memory.content_log import add_used_topic
                add_used_topic(script_data.get("used_topic_seed", script_data["title"]), int(base_fmt))'''
text = text.replace(f4_upload, '')
text = text.replace('                with open(script_path, "w") as f:\n                    json.dump(script_data, f)', f4_script)


with open("main.py", "w") as f:
    f.write(text)
