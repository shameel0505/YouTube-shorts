"""
Visual test script — renders a video for any format using Kokoro TTS.
Bypasses all Gemini API calls. Use this to preview caption/overlay changes.

Usage:
  python test_visuals.py          # tests Format 1 (facts)
  python test_visuals.py --format 2    # tests Format 2 (thriller)
  python test_visuals.py --format 3    # tests Format 3 (dilemma)

Requires Kokoro-FastAPI server to be running:
  cd ~/Kokoro-FastAPI && python main.py
"""
import os
import sys
import argparse
import datetime
sys.path.insert(0, os.path.dirname(__file__))

_F1_SCRIPT = """
This city banned white paint in 1817. And nobody questioned it for two hundred years.
Curacao is a tiny island in the Caribbean. Its capital is painted in every color imaginable.
But there is no white. Not a single building.
... Now it gets worse.
The law was never written down. Not once in two hundred years.
A Dutch governor complained white walls gave him migraines in the tropical sun.
So the island just stopped. No debate. No vote.
... Plot twist.
The ban technically still exists today.
And because of that accidental rule, Willemstad became a UNESCO World Heritage Site.
One man's headache created one of the most photographed cities on Earth.
Think about that next time you repaint your walls.
"""

_F2_SCRIPT = """
She opened her eyes. The ceiling was wrong.
This wasn't her apartment. This wasn't anywhere she'd ever been.
Her phone was gone. Her shoes were gone.
On the wall, written in red marker: "You were warned."
... But wait.
She recognised the handwriting.
It was hers.
She'd written it herself. Somehow. At some point she couldn't remember.
The door handle rattled from the outside.
Someone knew she was awake.
... Come back tomorrow to find out what happens.
"""

_F3_SCRIPT = """
You've been best friends with someone for fifteen years.
Yesterday, they told you they've been taking money from the charity they run.
Not a lot. But enough. They're paying off a medical debt for their kid.
They're begging you not to say anything.
The charity helps homeless families. Real people. Real kids.
But so does your friend, in their own way.
You know both sides. You feel both pulls.
... What would you do?
"""

_F3_CLOSING_Q = "What would you do?"

SCRIPTS = {
    "1": (_F1_SCRIPT, None),
    "2": (_F2_SCRIPT, None),
    "3": (_F3_SCRIPT, _F3_CLOSING_Q),
}

def run_test(fmt: str):
    script_text, closing_q = SCRIPTS[fmt]
    script_text = script_text.strip()

    from generator.voiceover import generate_voiceover
    from video.captions import transcribe_audio
    from video.footage import fetch_footage
    from video.editor import build_video

    print(f"\n🧪 Testing Format {fmt}")
    print("─" * 40)

    print("🎙️  Generating voiceover via Kokoro...")
    audio_path, duration = generate_voiceover(script_text, output_filename=f"voiceover_test_f{fmt}.mp3")
    print(f"   Duration: {duration:.1f}s")

    print("📄 Transcribing captions...")
    captions = transcribe_audio(audio_path, words_per_caption=3)
    print(f"   {len(captions)} chunks from {sum(len(c['words']) for c in captions)} words")

    print("🎬 Selecting gameplay footage...")
    footage = fetch_footage()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_f{fmt}_{ts}.mp4"

    print("🎞️  Rendering video...")
    path = build_video(footage, audio_path, captions, duration, filename, closing_question=closing_q)
    print(f"\n✅ Done! Output: {path}")

    import subprocess
    subprocess.Popen(["open", path])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual test for all 3 video formats")
    parser.add_argument("--format", choices=["1", "2", "3"], default="1")
    args = parser.parse_args()
    run_test(args.format)
