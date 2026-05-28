import os
import textwrap
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip, TextClip, CompositeAudioClip,
)
from moviepy.video.fx.all import crop, resize
from config import (VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
                    CAPTION_FONT_SIZE, CAPTION_COLOR, CAPTION_STROKE_COLOR,
                    CAPTION_STROKE_WIDTH, BACKGROUND_MUSIC_PATH, MUSIC_VOLUME,
                    TEMP_DIR, OUTPUT_DIR)
from video.captions import Caption

def build_video(footage_paths: list[str], audio_path: str, captions: list[Caption], audio_duration: float, output_filename: str) -> str:
    print("🎞️  Assembling video...")
    bg = _build_background(footage_paths, audio_duration)
    voice = AudioFileClip(audio_path)
    
    if BACKGROUND_MUSIC_PATH and os.path.isfile(BACKGROUND_MUSIC_PATH):
        try:
            music = AudioFileClip(BACKGROUND_MUSIC_PATH).volumex(MUSIC_VOLUME).audio_loop(duration=audio_duration)
            final_audio = CompositeAudioClip([voice, music])
        except Exception as e:
            print(f"⚠️  Could not load background music: {e}")
            final_audio = voice
    else:
        final_audio = voice
        
    video = bg.set_audio(final_audio).set_duration(audio_duration)
    
    caption_clips = _build_caption_clips(captions, audio_duration)
    
    if caption_clips:
        final = CompositeVideoClip([video] + caption_clips)
    else:
        final = video
        
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    final.write_videofile(
        output_path, 
        fps=VIDEO_FPS, 
        codec="libx264", 
        audio_codec="aac", 
        bitrate="6000k", 
        audio_bitrate="192k", 
        preset="fast", 
        threads=4, 
        verbose=False, 
        logger=None
    )
    
    print(f"✅ Video exported: {output_path}")
    return output_path

def _build_background(footage_paths: list[str], duration: float):
    if not footage_paths:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(10, 10, 20), duration=duration)
        
    clips = []
    for path in footage_paths:
        try:
            clip = VideoFileClip(path, audio=False)
            clip = _crop_to_vertical(clip)
            clips.append(clip)
        except Exception as e:
            print(f"⚠️  Skipping clip {path}: {e}")
            
    if not clips:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(10, 10, 20), duration=duration)
        
    if len(clips) > 1:
        combined = concatenate_videoclips(clips, method="compose")
    else:
        combined = clips[0]
        
    if combined.duration < duration:
        loops_needed = int(duration / combined.duration) + 1
        combined = concatenate_videoclips([combined] * loops_needed, method="compose")
        
    combined = combined.subclip(0, duration)
    combined = combined.fl_image(lambda frame: (frame * 0.65).astype("uint8"))
    
    return combined

def _crop_to_vertical(clip):
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    w, h = clip.size
    clip_ratio = w / h
    
    if clip_ratio > target_ratio:
        # Wider than target
        new_w = int(h * target_ratio)
        clip = crop(clip, width=new_w, height=h, x_center=w/2, y_center=h/2)
    elif clip_ratio < target_ratio:
        # Taller than target
        new_h = int(w / target_ratio)
        clip = crop(clip, width=w, height=new_h, x_center=w/2, y_center=h/2)
        
    return resize(clip, newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))

def _build_caption_clips(captions: list[Caption], video_duration: float) -> list:
    if not captions:
        return []
        
    y_position = int(VIDEO_HEIGHT * 0.72)
    clips = []
    
    for cap in captions:
        if cap.start >= video_duration:
            continue
            
        end = min(cap.end, video_duration)
        dur = end - cap.start
        
        if dur <= 0:
            continue
            
        text = "\n".join(textwrap.wrap(cap.text, width=18))
        
        try:
            try:
                txt_clip = TextClip(
                    text,
                    fontsize=CAPTION_FONT_SIZE,
                    color=CAPTION_COLOR,
                    font="Arial-Bold",
                    stroke_color=CAPTION_STROKE_COLOR,
                    stroke_width=CAPTION_STROKE_WIDTH,
                    method="caption",
                    size=(VIDEO_WIDTH - 80, None),
                    align="center",
                )
            except Exception:
                # Fallback font
                txt_clip = TextClip(
                    text,
                    fontsize=CAPTION_FONT_SIZE,
                    color=CAPTION_COLOR,
                    font="DejaVu-Sans-Bold",
                    stroke_color=CAPTION_STROKE_COLOR,
                    stroke_width=CAPTION_STROKE_WIDTH,
                    method="caption",
                    size=(VIDEO_WIDTH - 80, None),
                    align="center",
                )
                
            txt_clip = (txt_clip
                .set_start(cap.start)
                .set_duration(dur)
                .set_position(("center", y_position))
            )
            clips.append(txt_clip)
        except Exception as e:
            print(f"⚠️  Could not create text clip for '{text}': {e}")
            
    return clips
