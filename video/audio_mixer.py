import os
import random
import subprocess
from pydub import AudioSegment
from config import ASSETS_MUSIC_DIR, ASSETS_SFX_DIR, MUSIC_VOLUME, AUDIO_TARGET_LUFS, TEMP_DIR

def mix_audio(voice_path: str, fmt: int, duration: float, sfx_triggers: list[float]) -> str:
    """
    Mixes voiceover with format-specific background music, adds SFX at specified 
    timestamps, and normalizes the final mix to target LUFS.
    """
    print(f"🎵 Mixing audio for Format {fmt}...")
    
    # 1. Load voiceover
    voice = AudioSegment.from_file(voice_path)
    final_audio = voice
    
    # 2. Add background music
    subfolder_map = {1: "facts", 2: "thriller", 3: "dilemma"}
    music_dir = os.path.join(ASSETS_MUSIC_DIR, subfolder_map.get(fmt, ""))
    
    music_clips = []
    if os.path.exists(music_dir):
        music_clips = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith((".mp3", ".wav"))]
        
    if music_clips:
        chosen_music = random.choice(music_clips)
        music = AudioSegment.from_file(chosen_music)
        
        # Adjust volume based on user request (15%)
        # PyDub handles volume in dB. A rough approximation for 15% linear is -16.5 dB.
        # But we'll use a dynamic gain adjustment.
        # Let's say music should be X dB lower than voice.
        # We'll apply a flat reduction of -18 dB to the music.
        music = music - 18
        
        # Loop music to fit duration
        while len(music) < len(voice):
            music += music
        music = music[:len(voice)]
        
        # Mix
        final_audio = final_audio.overlay(music)
    
    # 3. Add Sound Effects
    if os.path.exists(ASSETS_SFX_DIR):
        # Whooshes on every background clip cut
        whoosh_path = os.path.join(ASSETS_SFX_DIR, "whoosh.mp3")
        if os.path.exists(whoosh_path):
            whoosh = AudioSegment.from_file(whoosh_path) - 5  # slightly quieter
            for trigger_sec in sfx_triggers:
                if trigger_sec > 0:
                    trigger_ms = int(trigger_sec * 1000)
                    final_audio = final_audio.overlay(whoosh, position=trigger_ms)
        
        # Format 2: Dramatic sting in final 2 seconds
        if fmt == 2:
            sting_path = os.path.join(ASSETS_SFX_DIR, "sting.mp3")
            if os.path.exists(sting_path):
                sting = AudioSegment.from_file(sting_path)
                trigger_ms = max(0, int((duration - 2.0) * 1000))
                final_audio = final_audio.overlay(sting, position=trigger_ms)
                
        # Format 3: Bell/chime when closing question appears
        if fmt == 3:
            chime_path = os.path.join(ASSETS_SFX_DIR, "chime.mp3")
            if os.path.exists(chime_path):
                chime = AudioSegment.from_file(chime_path)
                trigger_ms = max(0, int((duration - 5.0) * 1000)) # CLOSING_Q_DURATION = 5.0
                final_audio = final_audio.overlay(chime, position=trigger_ms)

    # Export pre-normalized audio
    temp_out = os.path.join(TEMP_DIR, f"pre_norm_f{fmt}.mp3")
    final_audio.export(temp_out, format="mp3", bitrate="192k")
    
    # 4. Normalize to -14 LUFS using FFmpeg loudnorm filter
    normalized_out = os.path.join(TEMP_DIR, f"mixed_audio_f{fmt}.mp3")
    
    try:
        cmd = [
            "ffmpeg", "-y", "-i", temp_out,
            "-af", f"loudnorm=I={AUDIO_TARGET_LUFS}:TP=-1.5:LRA=11",
            "-b:a", "192k",
            normalized_out
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return normalized_out
    except Exception as e:
        print(f"⚠️  LUFS normalization failed ({e}). Using un-normalized audio.")
        return temp_out
