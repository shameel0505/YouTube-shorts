with open("main.py", "r") as f:
    code = f.read()

# Replace ../memory/yt_tracker_f{fmt}.json with yt_tracker_f{fmt}.json
new_code = code.replace(
    'os.path.join(TEMP_DIR, f"../memory/yt_tracker_f{fmt}.json")',
    'os.path.join(TEMP_DIR, f"yt_tracker_f{fmt}.json")'
)

with open("main.py", "w") as f:
    f.write(new_code)
print("Path fixed!")
