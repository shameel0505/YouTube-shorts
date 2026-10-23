"""
Blender 3D Headless Render Engine Interface.
Locates the Blender executable and executes procedural 3D scene scripts in headless mode (-b).
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def find_blender_binary() -> str:
    """Locate the Blender executable on macOS / Linux."""
    # 1. Environment variable override
    env_bin = os.environ.get("BLENDER_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin

    # 2. Check PATH
    which_blender = subprocess.run(["which", "blender"], capture_output=True, text=True).stdout.strip()
    if which_blender and os.path.exists(which_blender):
        return which_blender

    # 3. macOS standard app locations
    macos_candidates = [
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/opt/homebrew/bin/blender",
        os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
    ]
    for c in macos_candidates:
        if os.path.exists(c):
            return c

    raise FileNotFoundError(
        "Blender executable not found. Please install Blender or set BLENDER_BIN environment variable."
    )


class BlenderRenderEngine:
    """Manages headless execution of procedural Blender Python scripts."""
    def __init__(self, blender_bin: str = None):
        self.blender_bin = blender_bin or find_blender_binary()
        self.templates_dir = Path(__file__).parent / "templates"

    def render_template(
        self,
        template_name: str,
        output_file: str | Path,
        params: dict = None,
        frames: int = 120,
        fps: int = 30,
        resolution: tuple[int, int] = (1920, 1080),
        engine: str = "BLENDER_EEVEE",
    ) -> Path:
        """
        Executes a template script inside Blender headlessly.
        """
        template_script = self.templates_dir / f"{template_name}.py"
        if not template_script.exists():
            raise FileNotFoundError(f"Blender template script '{template_name}' not found at {template_script}")

        output_path = Path(output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        params_json = json.dumps(params or {})

        cmd = [
            self.blender_bin,
            "--background",
            "--factory-startup",
            "--python", str(template_script),
            "--",
            "--output", str(output_path),
            "--params", params_json,
            "--frames", str(frames),
            "--fps", str(fps),
            "--width", str(resolution[0]),
            "--height", str(resolution[1]),
            "--engine", engine,
        ]

        print(f"🎬 [Blender] Invoking headless 3D render: {template_name} -> {output_path.name}")
        print(f"   Resolution: {resolution[0]}x{resolution[1]} @ {fps}fps | Frames: {frames} | Engine: {engine}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or "Traceback (most recent call last):" in result.stdout:
            print(f"❌ [Blender] Render error encountered (code: {result.returncode})")
            print("--- Blender Output ---")
            print(result.stdout[-1500:])
            if result.stderr:
                print("--- Blender STDERR ---")
                print(result.stderr[-1000:])
            raise RuntimeError(f"Blender execution failed:\n{result.stdout[-600:]}")


        if not output_path.exists():
            # Check if Blender appended frame numbers or format extension
            possible = list(output_path.parent.glob(f"{output_path.stem}*"))
            if possible:
                print(f"✅ [Blender] Render complete: {possible[0].name}")
                return possible[0]
            raise FileNotFoundError(f"Blender exited 0 but output file {output_path} was not found.")

        print(f"✅ [Blender] Render successfully created: {output_path.name} ({output_path.stat().st_size} bytes)")
        return output_path
