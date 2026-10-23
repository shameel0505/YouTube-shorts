#!/usr/bin/env python3
"""
Download verified public domain archival images from Wikimedia Commons using the MediaWiki API.
"""

import os
import urllib.request
import json

DEST_DIR = "/Users/shameel/Desktop/youtube/assets/archival/demon_core"
os.makedirs(DEST_DIR, exist_ok=True)

TITLES = [
    ("demon_core_setup.jpg", "File:The demon core.jpg"),
    ("slotin_portrait.jpg", "File:Slotin Los Alamos.jpg"),
    ("daghlian_portrait.gif", "File:Harry-K-Daghlian.gif"),
    ("slotin_criticality_drawing.jpg", "File:Slotin criticality drawing.jpg"),
    ("partially_reflected_core.jpg", "File:Partially-reflected-plutonium-sphere.jpeg")
]

HEADERS = {
    "User-Agent": "AntigravityMediaBot/1.0 (https://en.wikipedia.org; documentary_dev@astralyantra.com)"
}

print(f"📥 Resolving and downloading {len(TITLES)} archival assets via MediaWiki API...")

for local_name, wiki_title in TITLES:
    filepath = os.path.join(DEST_DIR, local_name)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        print(f"   ⏭️ Already present: {local_name} ({os.path.getsize(filepath):,} bytes)")
        continue

    # Query API for canonical URL
    api_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(wiki_title)}&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(api_url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        image_url = None
        for pid, pdata in pages.items():
            if "imageinfo" in pdata and len(pdata["imageinfo"]) > 0:
                image_url = pdata["imageinfo"][0]["url"]
                break
        
        if not image_url:
            print(f"   ⚠️ Could not resolve URL for {wiki_title}")
            continue

        # Download file
        dl_req = urllib.request.Request(image_url, headers=HEADERS)
        with urllib.request.urlopen(dl_req, timeout=20) as dl_resp, open(filepath, "wb") as f_out:
            f_out.write(dl_resp.read())
            
        print(f"   ✅ Successfully saved: {local_name} ({os.path.getsize(filepath):,} bytes)")
    except Exception as e:
        print(f"   ❌ Error with {wiki_title}: {e}")

print("🏁 All archival assets staged in assets/archival/demon_core!")
