import requests
import json

def upload_catbox(path):
    with open(path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=300,
        )
    resp.raise_for_status()
    return resp.text.strip()

videos = [
    {
        "path": "/Users/shameel/Desktop/youtube/experiments/videos/The Art of War_ A Brush with Destiny.MP4",
        "fmt": "2",
        "schedule_time": "2026-07-28T13:00:00+00:00",
        "caption": "The Purple Residue That Changed Everything\n\nImagine an 18-year-old chemist, alone in his attic lab, trying to cure malaria. 🧪 In 1856, William Henry Perkin was attempting to synthesize quinine from coal tar – a noble but utterly failed experiment. All he got was a sticky, black residue. 😩 Most people would toss it, right? But young Perkin, perhaps out of habit or sheer curiosity, decided to clean his flask with alcohol. 🧼 What happened next was a jaw-dropping burst of color: a stunning, vibrant purple! 💜\n\nThis wasn't just any purple; it was mauveine, the world's first synthetic dye! ✨ From that single, seemingly trivial decision, an entire industry was born. Fashion exploded with accessible, dazzling colors, democratizing vibrancy and making history literally more colorful! 👗🎨\n\nIt’s an incredible tale of how a tiny, almost overlooked action can unleash a cascade of world-altering changes. What's the most surprising accidental discovery you've ever heard of? Share your thoughts below! 👇\n\n#shorts #history #butterflyeffect #chemistry #invention #innovation #fashionhistory #accidentaldiscovery"
    },
    {
        "path": "/Users/shameel/Desktop/youtube/experiments/videos/Is Your Brain Living In A Selective Simulation?.MP4",
        "fmt": "3",
        "schedule_time": "2026-07-28T17:00:00+00:00",
        "caption": "Is Your Brain Living In A Selective Simulation?\n\nEver felt like the universe is playing tricks on you? 🤯 You learn a new word, buy a new car, and suddenly, POOF! ✨ It's *everywhere*. Is the simulation updating your personal reality? Or is your brain just pulling a fast one? 🤔\n\nDive deep into the fascinating \"glitch\" where perception clashes with reality. We uncover the mind-bending science behind why your brain suddenly highlights things you just learned, making it seem like they've multiplied overnight! 🚀 Prepare to question everything you thought you knew about your own awareness.\n\nWhat's the wildest coincidence your brain has ever manufactured for you? Share your stories below! 👇\n\n#shorts #psychology #brainglitch #cognitivescience #baadermeinhof #simulationtheory #mindblown #perception"
    },
    {
        "path": "/Users/shameel/Desktop/youtube/experiments/videos/The Town That Changed Its Name to Win Big ðŸŽ™ï¸ .MP4",
        "fmt": "4",
        "schedule_time": "2026-07-28T21:00:00+00:00",
        "caption": "The Town That Changed Its Name to Win Big 🎙️\n\nImagine a struggling town facing an uncertain future after WWII. What do you do? 🤔 The visionary leaders of Hot Springs, New Mexico, dared to dream bigger! ✨ They pulled off an absolutely brilliant, low-cost marketing coup that forever changed their destiny. Their audacious move wasn't just a name change; it was a strategic masterstroke that secured invaluable national publicity and revitalized an entire community! 🤯 From dusty desert to radio fame, this true story proves that ingenuity and a little daring can go a long, long way. 🚀 It’s a testament to collective vision and seizing an unprecedented opportunity. What's the boldest idea your community has ever embraced? Share in the comments! 👇\n\n#shorts #genius #truestory #loophole #marketingstrategy #newmexico #innovation #civicpride"
    }
]

pending = []

for v in videos:
    print(f"Uploading format {v['fmt']} to catbox.moe...")
    url = upload_catbox(v['path'])
    print(f"✅ Uploaded! URL: {url}")
    
    pending.append({
        "url": url,
        "caption": v['caption'],
        "schedule_time": v['schedule_time'],
        "fmt": v['fmt']
    })

with open('memory/pending_ig.json', 'w') as f:
    json.dump(pending, f)
print("✅ memory/pending_ig.json updated successfully with permanent catbox links!")
