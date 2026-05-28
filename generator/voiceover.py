import os
from google.cloud import texttospeech
import pydub
from config import TTS_LANGUAGE_CODE, TTS_VOICE_NAME, TTS_SPEAKING_RATE, TEMP_DIR

AVAILABLE_VOICES = {
    "male_deep":    "en-US-Neural2-D",
    "male_warm":    "en-US-Neural2-J",
    "female_clear": "en-US-Neural2-F",
    "female_warm":  "en-US-Neural2-H",
    "male_uk":      "en-GB-Neural2-B",
    "female_uk":    "en-GB-Neural2-A",
}

def generate_voiceover(script: str, output_filename: str = "voiceover.mp3") -> tuple[str, float]:
    client = texttospeech.TextToSpeechClient()
    
    clean_script = script.strip().replace("*", "").replace("#", "")
    
    synthesis_input = texttospeech.SynthesisInput(text=clean_script)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code=TTS_LANGUAGE_CODE, 
        name=TTS_VOICE_NAME
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, 
        speaking_rate=TTS_SPEAKING_RATE, 
        pitch=0.0, 
        volume_gain_db=2.0
    )
    
    response = client.synthesize_speech(
        input=synthesis_input, 
        voice=voice, 
        audio_config=audio_config
    )
    
    output_path = os.path.join(TEMP_DIR, output_filename)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
        
    duration = _get_audio_duration(output_path)
    print(f"✅ Voiceover generated: {output_path} ({duration:.1f}s)")
    
    return output_path, duration

def _get_audio_duration(filepath: str) -> float:
    try:
        audio = pydub.AudioSegment.from_mp3(filepath)
        return len(audio) / 1000.0
    except Exception:
        return 0.0
