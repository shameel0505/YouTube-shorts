import json

url = "https://storage.googleapis.com/shameel-ai-shorts-bucket/video_1785912124.mp4?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=storage-object-admin%40youtube-auto-497707.iam.gserviceaccount.com%2F20260805%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260805T064204Z&X-Goog-Expires=604800&X-Goog-SignedHeaders=host&X-Goog-Signature=01ea96a6bc15b0eeec444b2fac3b96f2c2df0c5a1e18559e2e973248b0ba42b49e312e08d53f22d7867b79f80a3ce14653fef342e9101cf439c1b94b0d3fde4ada3b82da9ba682a7fd67f74bc9663bed13db3cf649cd66cf995df1c8f3a4cfa61fcafb95aaa77c95662b7c27f214607d3f4ba8ba6bf2047f2a9987505997cb90594c12ec8993c440aafa0df290b3a4dcf69a20a5243c576047eb18f9de9d7f465d02bdfe9e2e95a2ee83c3dc1b7a64e8cd96dec4c70d01ca1f37b9d55e7e33454133dcbfb437955cb88d7dbb78d4a8782509d96b838516560b0b431eba247ec495959b938c935e1b420d8fe30e822a59677d18f9bcfc4a67e445956acd4efaec"
caption = "Newton's Apple: The Cosmos in a Single Fall\n\nAn apple falls, but Newton asks 'why?' 🍎 His curiosity didn't just reveal gravity; it unveiled the universe's secret laws. Discover how one question changed everything. What common phenomena do *you* question? 🤔\n\n#shorts #history #butterflyeffect #IsaacNewton #Science #Gravity #Physics #Enlightenment"

with open("memory/pending_ig.json", "r") as f:
    data = json.load(f)

data.append({
    "url": url,
    "caption": caption,
    "schedule_time": "2026-08-05T20:00:00+00:00",
    "fmt": "2"
})

with open("memory/pending_ig.json", "w") as f:
    json.dump(data, f)
