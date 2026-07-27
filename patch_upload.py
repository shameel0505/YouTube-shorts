import re
import os

with open("main.py", "r") as f:
    code = f.read()

def replace_upload(match):
    original = match.group(0)
    # Check if this format has IG upload logic
    if "IG_ACCESS_TOKEN" not in original:
        return original # skip if no IG logic (e.g. format 5)
        
    fmt_match = re.search(r'cleanup_notebooklm_state\((\d+)\)', original)
    if not fmt_match: return original
    fmt = fmt_match.group(1)
    
    # We will inject the yt_tracker check right after "if upload:"
    # We need to find the "if upload:" block, and replace everything up to the first IG_ACCESS_TOKEN check
    # But it's easier to just do simple string replacements.
    
    # Remove try/except block around IG upload:
    # 1. Remove "try:"
    # 2. Un-indent the IG upload lines
    # 3. Remove "except Exception as e:" and its block
    
    # Let's replace the whole block dynamically.
    lines = original.split("\n")
    new_lines = []
    in_yt_block = False
    in_ig_block = False
    skip_lines = 0
    
    for i, line in enumerate(lines):
        if skip_lines > 0:
            skip_lines -= 1
            continue
            
        if "if upload:" in line:
            new_lines.append(line)
            new_lines.append(f'            import json')
            new_lines.append(f'            yt_tracker = os.path.join(TEMP_DIR, f"../memory/yt_tracker_f{{fmt}}.json")')
            new_lines.append(f'            if os.path.exists(yt_tracker):')
            new_lines.append(f'                with open(yt_tracker, "r") as f:')
            new_lines.append(f'                    result = json.load(f)')
            new_lines.append(f'                log(f"⏭️ YouTube already uploaded: {{result.get(\'url\')}}", fmt)')
            new_lines.append(f'            else:')
            in_yt_block = True
            continue
            
        if "from config import IG_ACCESS_TOKEN" in line:
            in_yt_block = False
            # Close YT block
            new_lines.append(f'                with open(yt_tracker, "w") as f:')
            new_lines.append(f'                    json.dump(result, f)')
            new_lines.append("")
            new_lines.append(line)
            continue
            
        if in_yt_block:
            # indent it
            new_lines.append("    " + line)
            continue
            
        if "try:" in line and "IG_ACCESS_TOKEN" in "\n".join(lines[max(0, i-2):i+2]):
            # skip the "try:" line
            continue
            
        if "except Exception" in line and "IG Upload Failed" in lines[i+1]:
            # skip the except block
            skip_lines = 1
            # We are done with IG block, so we can also add the file removal here
            new_lines.append(f'            if os.path.exists(yt_tracker):')
            new_lines.append(f'                os.remove(yt_tracker)')
            continue
            
        if "ig_post_id =" in line or "log(\"📸 Uploading" in line or "caption =" in line or "result[\"ig_post_id\"]" in line:
            # un-indent by 4 spaces because we removed "try:"
            new_lines.append(line.replace("    ", "", 1))
            continue
            
        new_lines.append(line)
        
    return "\n".join(new_lines)

# Find each format's run function block
pattern = re.compile(r'        if upload:\n.*?cleanup_notebooklm_state\(\d+\)', re.DOTALL)
new_code = pattern.sub(replace_upload, code)

with open("main.py", "w") as f:
    f.write(new_code)
print("Patched formats successfully!")
