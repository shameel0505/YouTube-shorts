from generator.script import generate_long_video
import json

try:
    data = generate_long_video(retries=1)
    print("KEYS:", list(data.keys()))
    print("TOPIC:", data.get("topic"))
    print("TITLE:", data.get("title"))
    print("WORDS IN SCRIPT:", len(data.get("script", "").split()))
    print("NBLM INSTRUCTIONS:", data.get("notebooklm_instructions"))
except Exception as e:
    print("FAILED:", e)
