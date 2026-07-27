import re

with open("main.py", "r") as f:
    code = f.read()

# Remove 'import json' that are indented (inside functions)
new_code = re.sub(r'^\s+import json\s*\n', '', code, flags=re.MULTILINE)

with open("main.py", "w") as f:
    f.write(new_code)
print("Removed nested imports!")
