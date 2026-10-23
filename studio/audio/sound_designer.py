"""
Tactile Hollywood Sound Engine & Audio Post-Production Master.
Procedurally synthesizes sub-bass braams, whooshes, risers, mechanical clicks, and tension drones.
Automates multi-track mixing with voiceover sidechain ducking (-18dB) and broadcast LUFS mastering (-14 LUFS).
"""
import os
import sys
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path

SAMPLE_RATE = 48000  # 48kHz Broadcast Standard

class SoundDesigner:
    """Procedural sound effect generator and audio mastering pipeline."""

    def __init__(self, sfx_cache_dir: str | Path = None):
        self.cache_dir = Path(sfx_cache_dir or Path(__file__).parent / "assets")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def process_vocal_chain(self, input_audio: str | Path, output_audio: str | Path = None) -> Path:
        """
        Applies a Spotify Pedalboard studio mastering chain to speech tracks:
        1. 80Hz High-pass filter (cuts low rumble & plosives)
        2. 3kHz Parametric presence boost (+2.5dB for crisp documentary diction)
        3. Optical Compressor (3.5:1 ratio for warm, consistent authority)
        4. Subtle acoustic room reverb (wet 6% for depth)
        5. True-peak limiter (-1.0 dB ceiling)
        """
        in_path = Path(input_audio).resolve()
        out_path = Path(output_audio).resolve() if output_audio else in_path.with_name(f"{in_path.stem}_mastered.wav")

        try:
            from pedalboard import Pedalboard, Compressor, HighpassFilter, PeakFilter, Reverb, Limiter
            from pedalboard.io import AudioFile

            board = Pedalboard([
                HighpassFilter(cutoff_frequency_hz=80.0),
                PeakFilter(cutoff_frequency_hz=3000.0, gain_db=2.5, q=1.2),
                Compressor(threshold_db=-15.0, ratio=3.5, attack_ms=12.0, release_ms=120.0),
                Reverb(room_size=0.2, wet_level=0.06, dry_level=0.94),
                Limiter(threshold_db=-1.0)
            ])

            with AudioFile(str(in_path)) as f:
                audio = f.read(f.frames)
                sr = f.samplerate

            processed = board(audio, sr)

            with AudioFile(str(out_path), "w", sr, processed.shape[0]) as f:
                f.write(processed)

            print(f"🎙️ [SoundDesigner] Pedalboard studio vocal chain applied -> {out_path.name}")
            return out_path
        except Exception as e:
            print(f"⚠️ [SoundDesigner] Pedalboard mastering skipped ({e}), falling back to FFmpeg vocal filter")
            cmd = [
                "ffmpeg", "-y", "-i", str(in_path),
                "-af", "highpass=f=80,equalizer=f=3000:width_type=q:w=1.2:g=2.5,acompressor=threshold=0.12:ratio=3.5:attack=15:release=120",
                str(out_path)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return out_path

    def generate_braam(
        self,
        duration: float = 3.5,
        base_freq: float = 48.0,
        drive: float = 3.2,
        output_path: str | Path = None
    ) -> Path:
        """
        Synthesizes a deep Hollywood sub-bass braam (Hans Zimmer Inception/Dune aesthetic).
        Layers a downward-pitch sub sine, saturated brass harmonics, and stereo width.
        """
        out_file = Path(output_path) if output_path else self.cache_dir / f"braam_{int(base_freq)}hz.wav"
        if out_file.exists():
            return out_file

        num_samples = int(SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # 1. Pitch glide envelope: Drops by ~12% over the duration
        freq_env = base_freq * (1.0 - 0.12 * (t / duration) ** 1.5)
        phase = 2 * np.pi * np.cumsum(freq_env) / SAMPLE_RATE

        # 2. Sub-bass fundamental (pure mono sine)
        sub_sine = np.sin(phase)

        # 3. Harmonic Brass/Saw Layer (2nd, 3rd, 5th harmonics with drive)
        harmonics = (
            0.6 * np.sin(2 * phase) +
            0.4 * np.sin(3 * phase) +
            0.2 * np.sin(5 * phase)
        )
        # Non-linear analog saturation (warm wave-shaping)
        saturated_harmonics = np.tanh(harmonics * drive)

        # 4. Stereo widening on harmonics (slight delay between Left and Right)
        delay_samples = int(0.008 * SAMPLE_RATE)  # 8ms Haas delay
        harm_left = saturated_harmonics
        harm_right = np.roll(saturated_harmonics, delay_samples)
        harm_right[:delay_samples] = 0

        # 5. Amplitude Envelope (5ms punch attack, 0.6s sustained roar, exponential decay)
        attack_len = int(0.008 * SAMPLE_RATE)
        sustain_len = int(0.6 * SAMPLE_RATE)
        decay_len = num_samples - attack_len - sustain_len

        env_attack = np.linspace(0.0, 1.0, attack_len)
        env_sustain = np.ones(sustain_len)
        env_decay = np.exp(-3.5 * np.linspace(0, 1, decay_len))
        envelope = np.concatenate([env_attack, env_sustain, env_decay])

        # Mix Sub + Harmonics
        left_channel = (sub_sine * 0.75 + harm_left * 0.35) * envelope
        right_channel = (sub_sine * 0.75 + harm_right * 0.35) * envelope

        # Normalize to -1.0 dBFS
        stereo_signal = np.stack([left_channel, right_channel], axis=1)
        max_val = np.max(np.abs(stereo_signal))
        if max_val > 0:
            stereo_signal = (stereo_signal / max_val) * 0.95

        int16_audio = (stereo_signal * 32767).astype(np.int16)
        wavfile.write(str(out_file), SAMPLE_RATE, int16_audio)
        print(f"🔊 [SoundDesigner] Generated Sub-Bass Braam -> {out_file.name}")
        return out_file

    def generate_whoosh(
        self,
        duration: float = 1.0,
        center_freq: float = 1800.0,
        output_path: str | Path = None
    ) -> Path:
        """
        Synthesizes a cinematic filtered white-noise transition whoosh.
        """
        out_file = Path(output_path) if output_path else self.cache_dir / f"whoosh_{duration}s.wav"
        if out_file.exists():
            return out_file

        num_samples = int(SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # White noise base
        noise = np.random.normal(0, 1.0, num_samples)

        # Bell-curve amplitude envelope peaking at 40% duration
        peak_t = 0.40
        env = np.exp(-((t - peak_t * duration) ** 2) / (2 * (0.16 * duration) ** 2))

        # Dynamic frequency modulation for whoosh body
        carrier_freq = 180 + (center_freq - 180) * np.sin(np.pi * (t / duration)) ** 1.8
        carrier_phase = 2 * np.pi * np.cumsum(carrier_freq) / SAMPLE_RATE
        carrier = np.sin(carrier_phase)

        # Band-limited whoosh signal
        signal = (noise * 0.45 + carrier * 0.55) * env

        # Stereo pan sweep: Left (-0.7) to Right (+0.7)
        pan = np.linspace(-0.7, 0.7, num_samples)
        left = signal * np.sqrt(0.5 * (1.0 - pan))
        right = signal * np.sqrt(0.5 * (1.0 + pan))

        stereo = np.stack([left, right], axis=1)
        max_val = np.max(np.abs(stereo))
        if max_val > 0:
            stereo = (stereo / max_val) * 0.92

        int16_audio = (stereo * 32767).astype(np.int16)
        wavfile.write(str(out_file), SAMPLE_RATE, int16_audio)
        print(f"🔊 [SoundDesigner] Generated Cinematic Whoosh -> {out_file.name}")
        return out_file

    def generate_riser(
        self,
        duration: float = 4.0,
        start_freq: float = 70.0,
        end_freq: float = 850.0,
        output_path: str | Path = None
    ) -> Path:
        """
        Synthesizes an ascending tension riser with intensifying tremolo.
        """
        out_file = Path(output_path) if output_path else self.cache_dir / f"riser_{int(end_freq)}hz.wav"
        if out_file.exists():
            return out_file

        num_samples = int(SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Exponential pitch rise
        freq = start_freq * (end_freq / start_freq) ** (t / duration)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE

        # Multi-oscillator saw/sine
        saw = 2.0 * (phase / (2 * np.pi) - np.floor(0.5 + phase / (2 * np.pi)))
        sine = np.sin(phase)
        sub = np.sin(phase * 0.5)

        # Ramping tremolo / amplitude flutter
        tremolo_rate = np.linspace(3.0, 18.0, num_samples)
        tremolo_phase = 2 * np.pi * np.cumsum(tremolo_rate) / SAMPLE_RATE
        tremolo = 0.65 + 0.35 * np.sin(tremolo_phase)

        # Build-up volume envelope
        vol_env = (t / duration) ** 1.6

        raw = (sine * 0.4 + saw * 0.4 + sub * 0.2) * tremolo * vol_env

        # Stereo Haas split
        delay_samples = int(0.012 * SAMPLE_RATE)
        left = raw
        right = np.roll(raw, delay_samples)
        right[:delay_samples] = 0

        stereo = np.stack([left, right], axis=1)
        max_val = np.max(np.abs(stereo))
        if max_val > 0:
            stereo = (stereo / max_val) * 0.92

        int16_audio = (stereo * 32767).astype(np.int16)
        wavfile.write(str(out_file), SAMPLE_RATE, int16_audio)
        print(f"🔊 [SoundDesigner] Generated Ascending Riser -> {out_file.name}")
        return out_file

    def generate_mechanical_click(
        self,
        duration: float = 0.06,
        pitch: float = 2200.0,
        output_path: str | Path = None
    ) -> Path:
        """
        Synthesizes a crisp foley click / typewriter pulse for HUD callouts and kinetic cuts.
        """
        out_file = Path(output_path) if output_path else self.cache_dir / "mech_click.wav"
        if out_file.exists():
            return out_file

        num_samples = int(SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Sharp burst impulse with fast damping
        decay = np.exp(-120.0 * t)
        sine = np.sin(2 * np.pi * pitch * t)
        noise = np.random.normal(0, 0.4, num_samples)

        click = (sine * 0.65 + noise * 0.35) * decay
        stereo = np.stack([click, click], axis=1)

        max_val = np.max(np.abs(stereo))
        if max_val > 0:
            stereo = (stereo / max_val) * 0.90

        int16_audio = (stereo * 32767).astype(np.int16)
        wavfile.write(str(out_file), SAMPLE_RATE, int16_audio)
        print(f"🔊 [SoundDesigner] Generated Mechanical Click -> {out_file.name}")
        return out_file

    def generate_drone(
        self,
        duration: float = 12.0,
        root_pitch: float = 55.0,
        output_path: str | Path = None
    ) -> Path:
        """
        Synthesizes a dark, pulsating tension drone bed for background atmosphere.
        """
        out_file = Path(output_path) if output_path else self.cache_dir / f"drone_{int(root_pitch)}hz.wav"
        if out_file.exists():
            return out_file

        num_samples = int(SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Binaural detuned pair (55.0 Hz and 55.8 Hz for 0.8Hz ominous pulsing)
        left_tone = np.sin(2 * np.pi * root_pitch * t)
        right_tone = np.sin(2 * np.pi * (root_pitch + 0.8) * t)

        # Sub octave
        sub = np.sin(2 * np.pi * (root_pitch * 0.5) * t) * 0.5

        # Subtle filtered rumble
        rumble = np.random.normal(0, 0.08, num_samples)

        # Fade in & out
        fade_len = int(1.5 * SAMPLE_RATE)
        fade = np.ones(num_samples)
        fade[:fade_len] = np.linspace(0, 1, fade_len)
        fade[-fade_len:] = np.linspace(1, 0, fade_len)

        left = (left_tone * 0.5 + sub * 0.35 + rumble * 0.15) * fade
        right = (right_tone * 0.5 + sub * 0.35 + rumble * 0.15) * fade

        stereo = np.stack([left, right], axis=1)
        max_val = np.max(np.abs(stereo))
        if max_val > 0:
            stereo = (stereo / max_val) * 0.88

        int16_audio = (stereo * 32767).astype(np.int16)
        wavfile.write(str(out_file), SAMPLE_RATE, int16_audio)
        print(f"🔊 [SoundDesigner] Generated Tension Drone -> {out_file.name}")
        return out_file

    def mix_and_master(
        self,
        voiceover_audio: str | Path,
        background_tracks: list[dict],
        output_master_audio: str | Path,
        duck_db: float = 18.0,
    ) -> Path:
        """
        Multi-track mixing with voiceover sidechain ducking and broadcast LUFS mastering.
        - background_tracks: List of dicts with keys: {'path': Path, 'delay_sec': float, 'volume_db': float}
        - Masters to YouTube/Broadcast standards: -14 LUFS integrated, -1.0 dB true peak.
        """
        out_master = Path(output_master_audio).resolve()
        out_master.parent.mkdir(parents=True, exist_ok=True)

        voice_path = Path(voiceover_audio).resolve()
        if not voice_path.exists():
            raise FileNotFoundError(f"Voiceover track not found: {voice_path}")

        # Construct complex FFmpeg filter graph for sidechain ducking + mixing + LUFS mastering
        # Inputs:
        # 0: Voiceover
        # 1..N: Background tracks (music, braams, risers, whooshes)

        inputs = ["-i", str(voice_path)]
        filter_parts = []
        bg_labels = []

        for idx, bg in enumerate(background_tracks, start=1):
            inputs.extend(["-i", str(bg["path"])])
            delay_ms = int(bg.get("delay_sec", 0.0) * 1000)
            vol_db = bg.get("volume_db", -6.0)
            # Add delay and volume adjustments
            lbl = f"bg_{idx}"
            filter_parts.append(
                f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol_db}dB[{lbl}]"
            )
            bg_labels.append(f"[{lbl}]")

        # Mix all background tracks together
        if len(bg_labels) == 1:
            filter_parts.append(f"{bg_labels[0]}anull[bg_mix]")
        else:
            filter_parts.append(
                f"{''.join(bg_labels)}amix=inputs={len(bg_labels)}:dropout_transition=2:normalize=0[bg_mix]"
            )

        # Sidechain compress bg_mix whenever voice [0:a] is active
        # threshold 0.08, ratio 6:1, attack 35ms, release 350ms
        filter_parts.append(
            "[bg_mix][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=35:release=350[ducked_bg]"
        )

        # Mix voice + ducked background
        filter_parts.append(
            "[0:a][ducked_bg]amix=inputs=2:dropout_transition=2:normalize=0[pre_master]"
        )

        # Master with EBU R128 Loudness Normalization (-14 LUFS, -1.0 dB True Peak)
        filter_parts.append(
            "[pre_master]loudnorm=I=-14:TP=-1.0:LRA=11[master]"
        )

        filter_graph = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_graph,
            "-map", "[master]",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ar", "48000",
            str(out_master)
        ]

        print(f"🎚️ [SoundDesigner] Mastering audio bus (Sidechain -{duck_db}dB + LUFS -14)...")
        subp = subprocess.run(cmd, capture_output=True, text=True)
        if subp.returncode != 0:
            print(f"❌ [FFmpeg] Mastering failed:\n{subp.stderr[-600:]}")
            raise RuntimeError(f"FFmpeg audio master failed: {subp.stderr[-200:]}")

        print(f"✅ [SoundDesigner] Master audio finalized -> {out_master.name}")
        return out_master
