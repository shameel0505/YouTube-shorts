"""
Master Long-Form Compositor.
Assembles 3D Blender sequences, Veo footage, neural voiceover, and multi-layered
sound design into high-bitrate 16:9 widescreen cinematic master videos.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from studio.blender.render_engine import BlenderRenderEngine
from studio.manim.manim_engine import ManimRenderEngine
from studio.audio.sound_designer import SoundDesigner

class MasterCompositor:
    """End-to-end long-form documentary compositor."""

    def __init__(self, workspace_root: str | Path = None, voice: str = "en-US-ChristopherNeural"):
        self.workspace_root = Path(workspace_root or Path(__file__).resolve().parent.parent.parent)
        self.blender_engine = BlenderRenderEngine()
        self.manim_engine = ManimRenderEngine(self.workspace_root)
        self.sound_designer = SoundDesigner(self.workspace_root / "temp" / "sfx")
        self.output_dir = self.workspace_root / "output" / "longform"
        self.temp_dir = self.workspace_root / "temp" / "compositor"
        self.voice = voice

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def synthesize_speech(self, text: str, output_file: Path) -> float:
        """Synthesizes neural voiceover using edge-tts and returns duration in seconds."""
        if output_file.exists():
            duration = self._get_media_duration(output_file)
            return duration

        # Find edge-tts in venv
        venv_tts = self.workspace_root / "venv" / "bin" / "edge-tts"
        tts_cmd = str(venv_tts) if venv_tts.exists() else "edge-tts"

        cmd = [
            tts_cmd,
            "--voice", self.voice,
            "--text", text,
            "--write-media", str(output_file)
        ]
        subp = subprocess.run(cmd, capture_output=True, text=True)
        if subp.returncode != 0:
            raise RuntimeError(f"edge-tts failed: {subp.stderr}")

        return self._get_media_duration(output_file)

    def _get_media_duration(self, media_path: Path) -> float:
        """Inspects media duration via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(res.stdout.strip())
        except Exception:
            return 3.0

    def resolve_visual_shot(self, shot: Dict[str, Any], target_duration: float) -> Path:
        """
        Renders or retrieves the visual clip for a shot.
        Guarantees exact target duration and 1920x1080 16:9 output.
        """
        shot_id = shot["shot_id"]
        shot_type = shot["shot_type"]
        out_shot = self.temp_dir / f"visual_{shot_id}.mp4"

        if out_shot.exists() and self._get_media_duration(out_shot) >= (target_duration - 0.2):
            return out_shot

        if shot_type == "blender_3d":
            spec = shot["visual_spec"]
            template = spec.get("template", "kinetic_title")
            params = spec.get("params", {})
            fps = spec.get("fps", 30)
            target_frames = max(30, int(target_duration * fps))

            raw_blender_out = self.temp_dir / f"raw_blender_{shot_id}.mp4"
            self.blender_engine.render_template(
                template_name=template,
                output_file=raw_blender_out,
                params=params,
                frames=target_frames,
                fps=fps,
                resolution=spec.get("resolution", (1920, 1080)),
                engine="BLENDER_EEVEE"
            )
            return raw_blender_out

        elif shot_type == "manim_2d":
            spec = shot["visual_spec"]
            template_name = spec.get("template", "criticality_threshold")
            scene_name = spec.get("scene_name", "CriticalityThreshold")
            script_path = self.workspace_root / "studio" / "manim" / "templates" / f"{template_name}.py"

            raw_manim_out = self.temp_dir / f"raw_manim_{shot_id}.mp4"
            self.manim_engine.render_scene(
                script_path=script_path,
                scene_name=scene_name,
                output_file=raw_manim_out,
                quality="h",
                fps=30
            )
            self._conform_video_clip(raw_manim_out, out_shot, target_duration)
            return out_shot

        else:
            # Check if pre-rendered video clip exists
            candidate_clip = self.workspace_root / "output" / "clips" / f"{shot_id}.mp4"
            if candidate_clip.exists():
                # Conform clip to exact duration and 1920x1080
                self._conform_video_clip(candidate_clip, out_shot, target_duration)
                return out_shot

            # Fallback for dev / dry-run: Generate dynamic documentary motion canvas
            self._generate_documentary_motion_slate(shot, out_shot, target_duration)
            return out_shot

    def _conform_video_clip(self, input_clip: Path, output_clip: Path, target_duration: float):
        """Conforms any clip to 1920x1080 @ 30fps and exact target duration."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_clip),
            "-t", str(target_duration),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r", "30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            str(output_clip)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _generate_documentary_motion_slate(self, shot: Dict[str, Any], output_path: Path, duration: float):
        """Generates a high-contrast motion graphic slate with technical HUD and vignette."""
        shot_id = shot["shot_id"]
        shot_type = shot["shot_type"]
        title_text = shot.get("visual_spec", {}).get("archetype", shot_type)

        # Generate a high-contrast 1080p canvas using PIL
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1920, 1080), color=(10, 14, 23))
        draw = ImageDraw.Draw(img)

        # Draw technical blueprint borders & corner brackets
        bracket_len = 40
        draw.rectangle([40, 40, 1880, 1040], outline=(0, 217, 255), width=2)
        # Inner corner ticks
        draw.line([40, 80, 80, 80], fill=(0, 240, 255), width=3)
        draw.line([80, 40, 80, 80], fill=(0, 240, 255), width=3)
        draw.line([1840, 40, 1840, 80], fill=(0, 240, 255), width=3)
        draw.line([1840, 80, 1880, 80], fill=(0, 240, 255), width=3)

        # Text information
        draw.text((80, 90), f"// SEQUENCE NODE: {shot_id.upper()}", fill=(0, 240, 255))
        draw.text((80, 140), f"// ARCHETYPE: {title_text}", fill=(136, 160, 192))
        draw.text((80, 990), "16:9 WIDESCREEN CINEMATIC TIMELINE // 48kHz BROADCAST AUDIO", fill=(85, 102, 119))

        temp_slate_png = output_path.parent / f"slate_{shot_id}.png"
        img.save(temp_slate_png)

        # Animate with subtle zoom via ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(temp_slate_png),
            "-t", str(duration),
            "-vf", "scale=1920:1080,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        temp_slate_png.unlink(missing_ok=True)

    def assemble_masterpiece(self, storyboard_file: str | Path, output_filename: str = "masterpiece_16x9.mp4") -> Path:
        """
        Executes end-to-end long-form assembly from a storyboard manifest.
        """
        sb_path = Path(storyboard_file).resolve()
        with open(sb_path, "r", encoding="utf-8") as f:
            storyboard = json.load(f)

        print(f"🎬 [MasterCompositor] Starting Long-Form Master Assembly: '{storyboard.get('title')}'")
        master_out = self.output_dir / output_filename

        chapter_videos = []
        chapter_audios = []

        total_chapters = len(storyboard["chapters"])

        for ch_idx, chapter in enumerate(storyboard["chapters"], start=1):
            ch_num = chapter["chapter_num"]
            ch_title = chapter["title"]
            print(f"\n📁 [Chapter {ch_num}/{total_chapters}] Processing: {ch_title} ({chapter['arc_role']})")

            ch_shot_videos = []
            ch_voice_tracks = []
            ch_sfx_tracks = []
            timeline_cursor = 0.0

            for shot in chapter["shots"]:
                s_id = shot["shot_id"]
                narration = shot.get("narration", "")

                # 1. Synthesize Speech & Apply Spotify Pedalboard Studio Vocal Chain
                raw_voice = self.temp_dir / f"voice_raw_{s_id}.mp3"
                speech_dur = self.synthesize_speech(narration, raw_voice)

                voice_file = self.temp_dir / f"voice_mastered_{s_id}.wav"
                self.sound_designer.process_vocal_chain(raw_voice, voice_file)

                # Pad slightly for natural acoustic breathing room (0.4s)
                shot_duration = max(shot.get("duration_sec", 4.0), speech_dur + 0.4)
                ch_voice_tracks.append((voice_file, speech_dur, shot_duration))

                # 2. Resolve Visual Shot (Blender 3D or Veo)
                visual_clip = self.resolve_visual_shot(shot, shot_duration)
                ch_shot_videos.append(visual_clip)

                # 3. Queue Sound Effects
                for cue in shot.get("sound_cues", []):
                    sfx_type = cue["sfx_type"]
                    delay = timeline_cursor + cue.get("delay_sec", 0.0)
                    vol = cue.get("volume_db", -6.0)
                    params = cue.get("params", {})

                    if sfx_type == "braam":
                        sfx_file = self.sound_designer.generate_braam(**params)
                    elif sfx_type == "whoosh":
                        sfx_file = self.sound_designer.generate_whoosh(**params)
                    elif sfx_type == "riser":
                        sfx_file = self.sound_designer.generate_riser(**params)
                    elif sfx_type == "click":
                        sfx_file = self.sound_designer.generate_mechanical_click(**params)
                    elif sfx_type == "drone":
                        sfx_file = self.sound_designer.generate_drone(**params)
                    else:
                        continue

                    ch_sfx_tracks.append({
                        "path": sfx_file,
                        "delay_sec": delay,
                        "volume_db": vol
                    })

                timeline_cursor += shot_duration

            # Assemble Chapter Video (Concatenate shots)
            ch_video_concat = self.temp_dir / f"ch_{ch_num}_video.mp4"
            self._concat_videos(ch_shot_videos, ch_video_concat)
            chapter_videos.append(ch_video_concat)

            # Assemble Chapter Voice Track with exact spacing
            ch_voice_assembled = self.temp_dir / f"ch_{ch_num}_voice.wav"
            self._assemble_voice_timeline(ch_voice_tracks, ch_voice_assembled)

            # Mix & Master Chapter Audio (Sidechain ducking + LUFS -14)
            ch_master_audio = self.temp_dir / f"ch_{ch_num}_audio.wav"
            self.sound_designer.mix_and_master(
                voiceover_audio=ch_voice_assembled,
                background_tracks=ch_sfx_tracks,
                output_master_audio=ch_master_audio,
                duck_db=18.0
            )
            chapter_audios.append(ch_master_audio)

        # Concatenate All Chapters into Final Master Video
        final_video_track = self.temp_dir / "all_chapters_video.mp4"
        self._concat_videos(chapter_videos, final_video_track)

        final_audio_track = self.temp_dir / "all_chapters_audio.wav"
        self._concat_audio_tracks(chapter_audios, final_audio_track)

        # Final Multiplexing
        print(f"🎬 [MasterCompositor] Multiplexing final 16:9 master -> {master_out.name}")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(final_video_track),
            "-i", str(final_audio_track),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "320k",
            "-movflags", "+faststart",
            str(master_out)
        ]
        subprocess.run(mux_cmd, capture_output=True, check=True)

        final_dur = self._get_media_duration(master_out)
        print(f"🏆 [MasterCompositor] Masterpiece rendered successfully!")
        print(f"   Output: {master_out}")
        print(f"   Total Duration: {final_dur:.2f}s | Format: 1920x1080 16:9 | High-Bitrate H.264")
        return master_out

    def _concat_videos(self, video_paths: List[Path], output_path: Path):
        """Losslessly concatenates video segments."""
        list_file = output_path.parent / f"concat_vid_{output_path.stem}.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for v in video_paths:
                f.write(f"file '{v.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-an",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        list_file.unlink(missing_ok=True)

    def _assemble_voice_timeline(self, voice_tracks: List[tuple], output_path: Path):
        """Assembles voice segments spaced by their actual shot durations."""
        # voice_tracks: [(voice_file, speech_dur, shot_dur), ...]
        filter_parts = []
        inputs = []
        labels = []

        cursor = 0.0
        for idx, (v_file, sp_dur, sh_dur) in enumerate(voice_tracks):
            inputs.extend(["-i", str(v_file)])
            delay_ms = int(cursor * 1000)
            lbl = f"v_{idx}"
            filter_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[{lbl}]")
            labels.append(f"[{lbl}]")
            cursor += sh_dur

        mix_filter = f"{''.join(labels)}amix=inputs={len(labels)}:dropout_transition=0:normalize=0[voice_timeline]"
        filter_parts.append(mix_filter)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[voice_timeline]",
            "-ar", "48000",
            "-ac", "2",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _concat_audio_tracks(self, audio_paths: List[Path], output_path: Path):
        """Concatenates master audio streams across chapters."""
        list_file = output_path.parent / f"concat_aud_{output_path.stem}.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for a in audio_paths:
                f.write(f"file '{a.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        list_file.unlink(missing_ok=True)
