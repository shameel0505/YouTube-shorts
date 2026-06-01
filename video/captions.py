from faster_whisper import WhisperModel

_whisper_model = None

def _get_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        print("📦 Loading Whisper model (first run only)...")
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model

def transcribe_audio(audio_path: str, words_per_caption: int = 4) -> list[dict]:
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
                
        chunks = []
        for i in range(0, len(all_words), words_per_caption):
            chunk = all_words[i:i + words_per_caption]
            if not chunk:
                continue
            chunks.append({
                "words": chunk,
                "start": chunk[0]["start"],
                "end": chunk[-1]["end"]
            })
                
        print(f"✅ Generated {len(chunks)} caption chunks from {len(all_words)} words")
        return chunks
    except Exception as e:
        print(f"⚠️  Transcription failed: {e}")
        return []

