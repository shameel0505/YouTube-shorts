from generator.script import _call_gemini_for_script, _F5_PROMPT
import json

try:
    data = _call_gemini_for_script(
        _F5_PROMPT.format(avoid_clause=""),
        ["topic", "title"],
        retries=1
    )
    print("SUCCESS")
except Exception as e:
    pass
