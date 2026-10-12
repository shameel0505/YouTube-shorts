import os
import json
import subprocess
import google.generativeai as genai
import dotenv

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

print("📝 [Phase 1] Advanced Scripting & Storyboarding (High-Retention Hook)...")

prompt = """
You are a master YouTube Shorts director, cinematographer, and educational scriptwriter.
We need a "pitch-perfect," mind-blowing 60-second script about a fascinating scientific or historical anomaly. 
Pick one of these:
1. The terrifying reality of Deep-Sea Gigantism in the Mariana Trench.
2. The "Wood-Wide Web" (Avatar-like mycelial network).
3. The Observer Effect / Double Slit Experiment.

RULES FOR A HIGH-RETENTION PROFESSIONAL SHORT:
1. The first line (0-3s) MUST be an insane psychological or visual hook. No "Did you know". 
2. Fast pacing: We need EXACTLY 10 scenes, meaning the visual changes every ~4-5 seconds.
3. The B-roll prompts MUST dictate camera movement (e.g., "Fast drone push-in", "Macro slow-motion orbit").
4. The visual style must be consistent across all scenes (specify "Cinematic 8k, photorealistic" in every prompt).

Format:
{
  "topic": "The exact scientific topic",
  "title": "Catchy YouTube Short title",
  "scenes": [
    {
      "action": "[Camera Movement] + [Subject] + [Environment/Lighting]. Cinematic 8k, photorealistic.",
      "line": "The exact line of narration."
    },
    ... (exactly 10 scenes)
  ]
}
Respond ONLY with valid JSON.
"""

response = model.generate_content(prompt)
text = response.text.strip()
if text.startswith("```json"): text = text[7:]
if text.startswith("```"): text = text[3:]
if text.endswith("```"): text = text[:-3]

data = json.loads(text.strip())
print(f"✅ Generated script for: {data['title']}")

output_dir = "./output/experiments/pro_movie"
movie_toml_content = f"""# movie.toml — Professional Pipeline
schema_version = 1
title = "{data['title']}"
project = "pro-experiment-001"
output_dir = "{output_dir}"

[style]
look = "cinematic, documentary style"
negative = "text, watermark, low quality, cartoon"
suffix = "hyper-realistic, highly detailed, professional cinematography, IMAX 70mm, 8k, photorealistic."

[[characters]]
name = "Narrator"
appearance = "A professional, mysterious entity"
voice = "Algenib"  # PREMIUM GOOGLE FLOW VOICE (Gravelly, Low Pitch)

"""

for i, scene in enumerate(data['scenes']):
    action_text = scene['action'].replace('"', '')
    line_text = scene['line'].replace('"', '')
    
    movie_toml_content += f"""
[[scenes]]
id = "scene_{i+1}"
action = "{action_text}"
framing = "wide"
aspect = "9:16"
characters = ["Narrator"]
speaker = "Narrator"
line = "{line_text}"
"""

movie_toml_path = os.path.join(os.path.dirname(__file__), "pro_movie.toml")
with open(movie_toml_path, "w") as f:
    f.write(movie_toml_content)

print(f"\n✅ [Phase 2] Written pro_movie.toml using premium voice 'Algenib'.")
print("🎬 Launching gflow movie run to generate visuals (Veo) and TTS...")

cmd = ["gflow", "movie", "run", movie_toml_path, "--profile", "youtube"]
env = os.environ.copy()
env["GFLOW_CLI_HEADLESS"] = "0"
env["GFLOW_CLI_GEMINI_API_KEY"] = GEMINI_API_KEY
    
try:
    subprocess.run(cmd, env=env, check=True)
    print("🎉 gflow generation completed!")
    
    print("\n✍️ [Phase 3] Professional Assembly (Stitching, Music, Captions)...")
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from video.captions import transcribe_audio
    from video.editor import _build_caption_clips
    from video.audio_mixer import mix_audio
    from moviepy.editor import VideoFileClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
    
    handoff_path = os.path.join(os.path.dirname(__file__), "pro_movie-handoff.json")
    
    if os.path.exists(handoff_path):
        with open(handoff_path, "r") as f:
            handoff = json.load(f)
            
        clip_paths = []
        for c in handoff.get("clips", []):
            if c.get("file"):
                clip_paths.append(os.path.join(output_dir, c["file"]))
                
        if clip_paths:
            print(f"🔗 Concatenating {len(clip_paths)} clips...")
            video_clips = [VideoFileClip(p) for p in clip_paths]
            stitched_video = concatenate_videoclips(video_clips, method="compose")
            
            os.makedirs(output_dir, exist_ok=True)
            temp_voice = os.path.join(output_dir, "temp_voice.wav")
            stitched_video.audio.write_audiofile(temp_voice, fps=44100, logger=None)
            
            # --- Mix Audio (BGM + SFX) ---
            print("🎵 Adding Background Music & SFX...")
            sfx_triggers = [clip.duration for clip in video_clips][:-1] # Trigger on cuts
            
            # Since sfx_triggers for audio_mixer needs absolute timestamps:
            cumulative = 0
            abs_sfx_triggers = []
            for d in sfx_triggers:
                cumulative += d
                abs_sfx_triggers.append(cumulative)
                
            mixed_audio_path = mix_audio(temp_voice, fmt=2, duration=stitched_video.duration, sfx_triggers=abs_sfx_triggers)
            mixed_audio = AudioFileClip(mixed_audio_path)
            stitched_video = stitched_video.set_audio(mixed_audio)
            
            # --- Transcribe & Captions ---
            print("📝 Transcribing for Dynamic Captions...")
            captions = transcribe_audio(temp_voice, words_per_caption=4)
            caption_clips = _build_caption_clips(captions, stitched_video, fmt=1)
            
            final_video = CompositeVideoClip([stitched_video] + caption_clips)
            final_output_path = os.path.join(output_dir, "PITCH_PERFECT_FINAL.mp4")
            
            print(f"🎞️ Exporting Final Professional Video to {final_output_path}...")
            final_video.write_videofile(
                final_output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                logger=None
            )
            print(f"\n✅ ABSOLUTE PERFECTION! Video is ready: {final_output_path}")
            
            os.remove(temp_voice)
            for c in video_clips: c.close()
            stitched_video.close()
            mixed_audio.close()
        else:
            print("⚠️ No clips found in movie-handoff.json")
    else:
        print("⚠️ Could not find movie-handoff.json to stitch clips!")

except subprocess.CalledProcessError as e:
    print(f"❌ Process failed with exit code: {e.returncode}")
