import json
import time
import requests

with open('memory/pending_ig.json', 'r') as f:
    posts = json.load(f)

for post in posts:
    if 'uguu.se' in post['url']:
        print(f"Rescuing: {post['url']}")
        r = requests.get(post['url'])
        with open('temp.mp4', 'wb') as f_out:
            f_out.write(r.content)
        
        print("Uploading to litterbox...")
        with open('temp.mp4', 'rb') as f_in:
            r2 = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": f_in},
                timeout=120
            )
        new_url = r2.text.strip()
        print(f"New URL: {new_url}")
        post['url'] = new_url
        time.sleep(2)

with open('memory/pending_ig.json', 'w') as f:
    json.dump(posts, f)

print("Rescue complete.")
