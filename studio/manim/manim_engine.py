"""
Manim 2D Vector & Mathematical Motion Engine Interface.
Executes programmatic Manim Community scenes headlessly to generate
TED-Ed / 3Blue1Brown-grade vector animations, animated charts, and physics diagrams in 1080p.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

class ManimRenderEngine:
    """Headless render interface for Manim Community."""

    def __init__(self, workspace_root: str | Path = None):
        self.workspace_root = Path(workspace_root or Path(__file__).resolve().parent.parent.parent)
        self.manim_bin = self.workspace_root / "venv" / "bin" / "manim"
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def render_scene(
        self,
        script_path: str | Path,
        scene_name: str,
        output_file: str | Path,
        quality: str = "h",  # 'l' (480p), 'm' (720p), 'h' (1080p), 'k' (4k)
        fps: int = 30
    ) -> Path:
        """
        Renders a Manim Scene to a pristine 1080p MP4.
        """
        script_file = Path(script_path).resolve()
        if not script_file.exists():
            raise FileNotFoundError(f"Manim scene script not found: {script_file}")

        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        temp_media_dir = out_path.parent / f"manim_temp_{scene_name}_{os.getpid()}"
        temp_media_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.manim_bin),
            "render",
            f"-q{quality}",
            f"--fps", str(fps),
            "--media_dir", str(temp_media_dir),
            "-o", out_path.name,
            str(script_file),
            scene_name
        ]

        print(f"🎬 [Manim] Rendering 2D vector scene '{scene_name}' via {script_file.name}...")
        subp = subprocess.run(cmd, capture_output=True, text=True)

        if subp.returncode != 0:
            print(f"❌ [Manim] Render failed with exit code {subp.returncode}")
            print(subp.stderr[-1000:])
            shutil.rmtree(temp_media_dir, ignore_errors=True)
            raise RuntimeError(f"Manim render failed: {subp.stderr[-300:]}")

        # Locate the rendered video inside the media directory
        rendered_candidates = list(temp_media_dir.glob(f"**/{out_path.name}")) or list(temp_media_dir.glob("**/*.mp4"))
        if not rendered_candidates:
            shutil.rmtree(temp_media_dir, ignore_errors=True)
            raise FileNotFoundError(f"Manim finished but no MP4 output found for scene '{scene_name}'")

        shutil.move(str(rendered_candidates[0]), str(out_path))
        shutil.rmtree(temp_media_dir, ignore_errors=True)

        print(f"✅ [Manim] Vector scene rendered successfully -> {out_path.name} ({out_path.stat().st_size} bytes)")
        return out_path
