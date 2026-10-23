#!/usr/bin/env python3
"""
Generate and master the 30-second cold open audio for 'The 2-Millimeter Slip'
to prove broadcast fidelity, prosody, and -14 LUFS mastering.
"""

import os
import asyncio
import subprocess
import edge_tts

OUT_DIR = "/Users/shameel/Desktop/youtube/output/experiments/longform"
os.makedirs(OUT_DIR, exist_ok=True)

VOICEOVER_TEXT = (
    "In the spring of 1946, the United States spent two billion dollars building the most mathematically precise scientific apparatus on Earth. "
    "Yet the single thing standing between eight physicists and a lethal burst of prompt criticality... was a nine-inch flathead screwdriver that cost sixty-five cents."
)

RAW_VOICE_FILE = os.path.join(OUT_DIR, "cold_open_raw.mp3")
MASTERED_VOICE_FILE = os.path.join(OUT_DIR, "cold_open_mastered.wav")

async def generate_speech():
    print("🎙️ Generating neural documentary narration via edge-tts (en-US-ChristopherNeural)...")
    # Using ChristopherNeural with slight pace reduction for gravitas
    communicate = edge_tts.Communicate(
        text=VOICEOVER_TEXT,
        voice="en-US-ChristopherNeural",
        rate="-4%",
        pitch="-2Hz"
    )
    await communicate.save(RAW_VOICE_FILE)
    print(f"✅ Raw narration generated: {RAW_VOICE_FILE}")

def master_audio():
    print("🎛️ Mastering audio to broadcast standard (-14 LUFS, 80Hz high-pass, 3kHz presence boost)...")
    # ffmpeg filter chain: highpass 80Hz, subtle EQ presence boost at 3kHz, loudnorm to -14 LUFS
    cmd = [
        "ffmpeg", "-y", "-i", RAW_VOICE_FILE,
        "-af", "highpass=f=80,equalizer=f=3000:width_type=q:width=1.5:g=2.5,loudnorm=I=-14:LRA=7:TP=-1.5",
        "-c:a", "pcm_s16le", "-ar", "44100",
        MASTERED_VOICE_FILE
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Mastered audio deliverable ready: {MASTERED_VOICE_FILE}")

if __name__ == "__main__":
    asyncio.run(generate_speech())
    master_audio()
    # Check loudness with ffprobe/ebur128
    print("🔎 Running EBU R128 loudness verification...")
    probe_cmd = [
        "ffmpeg", "-i", MASTERED_VOICE_FILE,
        "-af", "ebur128=framelog=verbose",
        "-f", "null", "-"
    ]
    result = subprocess.run(probe_cmd, stderr=subprocess.PIPE, text=True)
    # Extract Integrated Loudness
    for line in result.stderr.splitlines():
        if "Integrated loudness:" in line or "I:" in line and "LUFS" in line:
            print(f"   📊 Loudness verdict: {line.strip()}")
            break
    print("🏁 Cold open audio benchmark complete!")
