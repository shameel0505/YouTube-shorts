import json
with open('memory/pending_ig.json', 'r') as f:
    data = json.load(f)

# Filter out format 2
new_data = [item for item in data if item.get('fmt') != '2']

with open('memory/pending_ig.json', 'w') as f:
    json.dump(new_data, f, indent=4)
