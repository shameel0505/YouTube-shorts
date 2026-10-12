import os
import sys
import json
import time
import subprocess
import re

# Add the parent directory to the path so we can import project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import GEMINI_API_KEY
import google.generativeai as genai
from generator.voiceover import generate_voiceover
from moviepy.editor import VideoFileClip, concatenate_videoclips

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "experiments", "custom_movie"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_script():
    print("📝 Generating custom 12-scene script...")
    prompt = """
    You are an expert YouTube Shorts scriptwriter. Write a 60-second, highly engaging script about:
    "The Terrifying Scale of the Universe (Bootes Void)".
    
    The script MUST be EXACTLY 12 scenes long. Each scene represents about 5 seconds of video.
    
    For each scene, provide:
    - "prompt": A highly detailed, cinematic 8K visual prompt for a video generator. Describe camera movement (e.g. "slow pan", "zoom in").
    - "narration": The spoken text for that 5-second scene. Use high retention hooks. Add ", ..." before major reveals for TTS pauses. No emojis.
    
    Output strictly valid JSON in this format:
    {
      "scenes": [
        {"prompt": "...", "narration": "..."},
        ...
      ]
    }
    """
    resp = model.generate_content(prompt)
    raw = resp.text.strip()
    if raw.startswith("```json"):
        raw = raw[7:-3]
    elif raw.startswith("```"):
        raw = raw[3:-3]
    return json.loads(raw)

def generate_veo_clip(scene_idx, prompt):
    print(f"🎬 Generating Veo clip {scene_idx + 1}/12...")
    cmd = [
        "gflow", "video", "t2v",
        prompt,
        "--aspect", "9:16",
        "--profile", "youtube",
        "--out-dir", OUTPUT_DIR,
        "--json"
    ]
    
    for attempt in range(3):
        print(f"Attempt {attempt+1}/3 for scene {scene_idx+1}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=120)
        except subprocess.TimeoutExpired:
            print(f"⚠️ Timeout on attempt {attempt+1}")
            continue
            
        try:
            data = json.loads(result.stdout)
            rel_path = data.get("path")
            if rel_path:
                abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', rel_path))
                print(f"✅ Saved clip {scene_idx + 1} to {abs_path}")
                return abs_path
        except json.JSONDecodeError:
            pass

        match = re.search(r'"path":\s*"([^"]+\.mp4)"', result.stderr)
        if match:
            rel_path = match.group(1).strip()
            abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', rel_path))
            print(f"✅ Saved clip {scene_idx + 1} to {abs_path}")
            return abs_path
            
    raise Exception(f"Failed to generate clip {scene_idx + 1} after 3 attempts.")

def main():
    OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "experiments", "custom_movie"))
    
    # 2. Voiceover (already generated)
    voice_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp', 'voiceover.mp3'))
    
    # 3. Visuals (All 12 successfully generated)
    clip_paths = [
        f"{OUTPUT_DIR}/761a808f-8693-4757-9c28-276cb4b4ca1a.mp4",
        f"{OUTPUT_DIR}/0a0a3f29-c2a3-48cb-b71d-25dac0f04dea.mp4",
        f"{OUTPUT_DIR}/9a2f0512-b7c9-42a9-a877-868c89f08637.mp4",
        f"{OUTPUT_DIR}/26336a58-a6a6-4013-afb6-a0ce33110aa0.mp4",
        f"{OUTPUT_DIR}/2b316303-9f4e-4186-bf38-02a47c922ccc.mp4",
        f"{OUTPUT_DIR}/d823c34f-6913-48eb-88e2-1d8fc1f0aefb.mp4",
        f"{OUTPUT_DIR}/d1bd3796-b9f3-48b2-9380-4f6eda288f90.mp4",
        f"{OUTPUT_DIR}/773741e0-7d0e-4466-afdc-5abbe4c49e02.mp4",
        f"{OUTPUT_DIR}/47d8c61f-a709-4101-8c04-18088ee765b6.mp4",
        f"{OUTPUT_DIR}/5722b1af-1dcf-48d8-87aa-a20323cef01a.mp4",
        f"{OUTPUT_DIR}/00df9c70-2163-42e9-b173-87f96e7afbfc.mp4",
        f"{OUTPUT_DIR}/065f0f5b-ea64-46ec-b016-74937ebc8c67.mp4"
    ]
        
    # 4. Stitching
    print("\n🧵 Stitching clips together...")
    clips = [VideoFileClip(p) for p in clip_paths]
    final_visuals = concatenate_videoclips(clips, method="compose")
    
    stitched_path = os.path.join(OUTPUT_DIR, "stitched_visuals.mp4")
    final_visuals.write_videofile(stitched_path, fps=30, codec="libx264", audio=False, preset="ultrafast")
    
    # 5. Final Assembly (Audio Mixing + Captions)
    print("\n✍️ Adding Captions, Background Music, and SFX...")
    sfx_triggers = [i * 5.0 for i in range(1, len(clip_paths))]
    
    final_output_path = os.path.join(OUTPUT_DIR, "PITCH_PERFECT_FINAL.mp4")
    
    from video.audio_mixer import mix_audio
    from video.captions import transcribe_audio
    from video.editor import _build_caption_clips
    from moviepy.editor import CompositeVideoClip, AudioFileClip
    
    mixed_audio_path = mix_audio(voice_path, 1, final_visuals.duration, sfx_triggers)
    
    video = VideoFileClip(stitched_path)
    audio = AudioFileClip(mixed_audio_path)
    
    if video.duration < audio.duration:
        from moviepy.video.fx.all import loop
        extra_time = audio.duration - video.duration
        last_clip = clips[-1].subclip(0, min(5.0, extra_time))
        if extra_time > 5.0:
             last_clip = loop(last_clip, duration=extra_time)
        video = concatenate_videoclips([video, last_clip])
        
    video = video.set_audio(audio)
    
    transcript = transcribe_audio(voice_path)
    # Corrected signature: _build_caption_clips(captions, video_clip, fmt)
    caption_clips = _build_caption_clips(transcript, video, 1)
    
    final_comp = CompositeVideoClip([video] + caption_clips)
    final_comp = final_comp.set_duration(audio.duration)
    
    final_comp.write_videofile(final_output_path, fps=30, codec="libx264", audio_codec="aac")
    print(f"\n🎉 SUCCESS! Final video saved to {final_output_path}")
    
    for c in clips:
        c.close()

if __name__ == "__main__":
    main()
