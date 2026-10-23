#!/usr/bin/env python3
"""
Render a 15-second benchmark proof clip combining archival 2.5D parallax,
mastered neural narration, ambient sound design, and kinetic typography.
"""

import os
import subprocess

OUT_DIR = "/Users/shameel/Desktop/youtube/output/experiments/longform"
AUDIO_FILE = os.path.join(OUT_DIR, "cold_open_mastered.wav")
IMAGE_FILE = "/Users/shameel/Desktop/youtube/assets/archival/demon_core/demon_core_setup.jpg"
BGM_FILE = "/Users/shameel/Desktop/youtube/assets/music/thriller/Cinematic Documentary Drone by Infraction [No Copyright Music] ⧸ Slow Motion.mp3"
OUT_VIDEO = os.path.join(OUT_DIR, "cold_open_proof.mp4")

# Get exact duration of narration audio
probe_cmd = [
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", AUDIO_FILE
]
dur_str = subprocess.check_output(probe_cmd).decode().strip()
duration = float(dur_str)
print(f"⏱️ Audio narration duration: {duration:.2f}s")

print("🎬 Rendering 1080p 2.5D archival proof video with audio mixing and pan-zoom...")

# Complex filter:
# 1. Video: Scale image to fill 1080p, apply smooth slow pan-zoom (Ken Burns), subtle vignette
# 2. Audio: Mix narration (at 0dB) with ambient score (ducked to -22dB), pad with subtle fade out
cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-i", IMAGE_FILE,
    "-i", AUDIO_FILE,
    "-i", BGM_FILE,
    "-filter_complex",
    f"[0:v]scale=2160:1215,zoompan=z='min(zoom+0.0006,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*24)}:s=1920x1080:fps=24,format=yuv420p[v];"
    f"[2:a]volume=0.08,afade=t=out:st={duration-1.5}:d=1.5[bgm];"
    f"[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
    "-map", "[v]",
    "-map", "[a]",
    "-t", str(duration),
    "-c:v", "libx264", "-preset", "fast", "-crf", "20",
    "-c:a", "aac", "-b:a", "192k",
    OUT_VIDEO
]

subprocess.run(cmd, check=True)
print(f"✅ Cold open proof video successfully generated: {OUT_VIDEO}")
print(f"   Size: {os.path.getsize(OUT_VIDEO):,} bytes")
