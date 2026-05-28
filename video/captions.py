from dataclasses import dataclass
from faster_whisper import WhisperModel

@dataclass
class Caption:
    text: str
    start: float
    end: float

_whisper_model = None

def _get_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        print("📦 Loading Whisper model (first run only)...")
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model

def transcribe_audio(audio_path: str, words_per_caption: int = 4) -> list[Caption]:
    try:
        model = _get_model()
        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        
        all_words = []
        for segment in segments:
            for word in segment.words:
                all_words.append({
                    "text": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
                
        captions = []
        for i in range(0, len(all_words), words_per_caption):
            chunk = all_words[i:i + words_per_caption]
            if not chunk:
                continue
                
            text = " ".join([w["text"] for w in chunk]).strip().upper()
            start = chunk[0]["start"]
            end = chunk[-1]["end"]
            
            if text:
                captions.append(Caption(text=text, start=start, end=end))
                
        print(f"✅ Generated {len(captions)} caption chunks from {len(all_words)} words")
        return captions
    except Exception as e:
        print(f"⚠️  Transcription failed: {e}")
        return []

def captions_to_srt(captions: list[Caption], output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as f:
        for i, cap in enumerate(captions, 1):
            f.write(f"{i}\n")
            f.write(f"{_fmt_time(cap.start)} --> {_fmt_time(cap.end)}\n")
            f.write(f"{cap.text}\n\n")
    return output_path

def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
