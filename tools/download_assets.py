import os
import subprocess

MUSIC_ASSETS = {
    "facts": [
        "https://www.youtube.com/watch?v=-Gel0z3lJms",
        "https://www.youtube.com/watch?v=0iFPI9EYqPU",
        "https://www.youtube.com/watch?v=S0STHSOPPSM"
    ],
    "thriller": [
        "https://www.youtube.com/watch?v=6OdwGfJAR1U",
        "https://www.youtube.com/watch?v=gUgyfUIhGQc",
        "https://www.youtube.com/watch?v=13aniTqzI9I"
    ],
    "dilemma": [
        "https://www.youtube.com/watch?v=hm0-ZTLRWEo",
        "https://www.youtube.com/watch?v=Ly9H63SLJJo",
        "https://www.youtube.com/watch?v=X9y5ka70Qto",
        "https://www.youtube.com/watch?v=sJfgTH39OCA"
    ]
}

def download_audio(url, output_dir):
    try:
        # Download best audio and convert to mp3
        subprocess.run([
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{output_dir}/%(title)s.%(ext)s",
            url
        ], check=True)
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")

def main():
    print("🎵 Starting background music asset download...")
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "music"))
    
    for folder, urls in MUSIC_ASSETS.items():
        target_dir = os.path.join(base_dir, folder)
        os.makedirs(target_dir, exist_ok=True)
        
        print(f"\n📂 Downloading {len(urls)} tracks to {target_dir}...")
        for url in urls:
            download_audio(url, target_dir)
            
    print("\n✅ Music downloads complete!")
    print("\n" + "="*50)
    print("🚨 ATTENTION: REQUIRED MANUAL ACTION 🚨")
    print("="*50)
    print("For Sound Effects, you must manually download 3 files from freesound.org")
    print("and place them in the 'assets/sfx' folder named EXACTLY:")
    print("  1. whoosh.mp3")
    print("  2. sting.mp3")
    print("  3. chime.mp3")
    print("="*50)

if __name__ == "__main__":
    main()
