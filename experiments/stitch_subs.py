import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from video.captions import transcribe_audio
from video.editor import _build_caption_clips
from moviepy.editor import VideoFileClip, CompositeVideoClip, concatenate_videoclips

output_dir = "./output/experiments/my_movie"
handoff_path = os.path.join(os.path.dirname(__file__), "movie-handoff.json")

print("✍️ Stitching existing clips and generating subtitles...")

if os.path.exists(handoff_path):
    with open(handoff_path, "r") as f:
        handoff = json.load(f)
        
    clip_paths = []
    for c in handoff.get("clips", []):
        if c.get("file"):
            p = os.path.join(output_dir, c["file"])
            if os.path.exists(p):
                clip_paths.append(p)
            else:
                print(f"⚠️ Missing clip: {p}")
                
    if len(clip_paths) == 10:
        print(f"🔗 Found 10 clips, concatenating...")
        video_clips = [VideoFileClip(p) for p in clip_paths]
        stitched_video = concatenate_videoclips(video_clips, method="compose")
        
        temp_audio = os.path.join(output_dir, "temp_extracted_audio.wav")
        stitched_video.audio.write_audiofile(temp_audio, fps=44100, logger=None)
        
        print("🎙️ Transcribing audio...")
        captions = transcribe_audio(temp_audio, words_per_caption=4)
        
        print("🎨 Building beautifully wrapped dynamic captions...")
        from video.editor import _build_caption_clips
        caption_clips = _build_caption_clips(captions, stitched_video, fmt=1)
        
        final_video = CompositeVideoClip([stitched_video] + caption_clips)
        final_output_path = os.path.join(output_dir, "final_narrated_subtitled.mp4")
        
        print(f"🎞️ Burning subtitles into {final_output_path}...")
        final_video.write_videofile(
            final_output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )
        print(f"\\n🎬 ABSOLUTE PERFECTION! Your 2026-grade video with FFmpeg Subtitles is ready at: {final_output_path}")
        
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
            
        for c in video_clips: c.close()
        stitched_video.close()
    else:
        print(f"⚠️ Found {len(clip_paths)} clips, expected 10.")
else:
    print("⚠️ Could not find movie-handoff.json!")
