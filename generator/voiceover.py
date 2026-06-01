"""
Voiceover generation via Kokoro-FastAPI (local TTS server).
Replaces Google Cloud Text-to-Speech.

Kokoro server must be running before this module is called.
  Local:  cd ~/Kokoro-FastAPI && python main.py
  GCP:    sudo systemctl start kokoro
"""
import os
import re
import sys
import requests
import pydub
from config import KOKORO_API_URL, KOKORO_VOICE, TEMP_DIR

# Available Kokoro voices for reference (set KOKORO_VOICE in .env)
AVAILABLE_VOICES = {
    "af_heart":   "Female — warm, conversational (default)",
    "af_bella":   "Female — smooth, storytelling",
    "af_nicole":  "Female — energetic, upbeat",
    "am_adam":    "Male — deep, authoritative",
    "am_michael": "Male — clear, neutral",
    "bf_emma":    "British Female — polished",
    "bm_george":  "British Male — dramatic",
}

# Re-hook phrases that get a text pause inserted BEFORE them for dramatic effect
_REHOOK_TRIGGERS = [
    "but wait",
    "now it gets",
    "plot twist",
    "i am not done",
    "but actually",
    "the real reason",
    "nobody saw",
    "this is where it gets",
    "here is the part",
    "not even the crazy",
    "come back tomorrow",
    "what would you do",
]

# Short power sentences (≤ this many words) get a pause AFTER them
_POWER_SENTENCE_MAX_WORDS = 4


def _health_check() -> bool:
    """Ping the Kokoro-FastAPI health endpoint. Returns True if server is up."""
    try:
        resp = requests.get(f"{KOKORO_API_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _inject_text_pauses(text: str) -> str:
    """
    Convert a plain script into Kokoro-friendly text by injecting
    comma-ellipsis pauses at dramatically appropriate positions.

    Kokoro uses punctuation for natural pacing — no SSML needed.
    """
    # Clean stray markdown/formatting that TTS would speak literally
    text = text.strip()
    text = text.replace("*", "").replace("#", "").replace("—", ",")
    # Normalise any leftover ellipsis into a single form
    text = re.sub(r'\.{2,}', ',', text)

    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    parts = []

    for sentence in raw_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        lower = sentence.lower()
        word_count = len(sentence.split())
        is_rehook = any(trigger in lower for trigger in _REHOOK_TRIGGERS)

        if is_rehook:
            # Long pause BEFORE the re-hook line
            parts.append(f"... {sentence}")
        elif word_count <= _POWER_SENTENCE_MAX_WORDS:
            # Short punchy sentence — pause AFTER it
            parts.append(f"{sentence} ...")
        else:
            parts.append(sentence)

    return " ".join(parts)


def generate_voiceover(script: str, output_filename: str = "voiceover.mp3") -> tuple[str, float]:
    """
    Generate a voiceover MP3 from a plain text script using Kokoro-FastAPI.
    Returns (output_path, duration_seconds).
    """
    # --- Health check ---
    if not _health_check():
        print()
        print("❌  Cannot reach the Kokoro-FastAPI TTS server.")
        print("    Please start it before running the pipeline:")
        print()
        print("    Local Mac:")
        print("      cd ~/Kokoro-FastAPI && python main.py")
        print()
        print("    GCP VM:")
        print("      sudo systemctl start kokoro")
        print()
        sys.exit(1)

    # --- Inject text-based pauses ---
    clean_script = _inject_text_pauses(script)

    # --- Call Kokoro API ---
    payload = {
        "model": "kokoro",
        "voice": KOKORO_VOICE,
        "input": clean_script,
        "response_format": "mp3",
    }

    resp = requests.post(
        f"{KOKORO_API_URL}/v1/audio/speech",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()

    # --- Write to disk ---
    output_path = os.path.join(TEMP_DIR, output_filename)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    duration = _get_audio_duration(output_path)
    print(f"✅ Voiceover generated: {output_path} ({duration:.1f}s)")
    return output_path, duration


def _get_audio_duration(filepath: str) -> float:
    """Return audio duration in seconds using pydub."""
    try:
        audio = pydub.AudioSegment.from_mp3(filepath)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"⚠️  Pydub duration error: {e}")
        return 0.0
