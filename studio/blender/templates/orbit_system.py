"""
Blender 3D Procedural Orbital Particle Field / Quantum Lattice Template.
Creates an atmospheric 3D particle swarm with concentric orbital rings,
luminous depth-of-field bokeh, and a floating camera pan.
Compatible with Blender 4.x / 5.x LTS.
"""
import sys
import os
import argparse
import json
import math
import random
from pathlib import Path
import bpy

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Render 3D Orbital Particle Field")
    parser.add_argument("--output", type=str, required=True, help="Path to output video file")
    parser.add_argument("--params", type=str, default="{}", help="JSON string of scene parameters")
    parser.add_argument("--frames", type=int, default=120, help="Total frame count")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--width", type=int, default=1920, help="Resolution width")
    parser.add_argument("--height", type=int, default=1080, help="Resolution height")
    parser.add_argument("--engine", type=str, default="BLENDER_EEVEE", help="Render engine")
    return parser.parse_args(argv)

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def create_emission_material(name: str, color: tuple, strength: float = 4.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (400, 0)

    emission = nodes.new(type="ShaderNodeEmission")
    emission.location = (150, 0)
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength

    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat

def build_orbital_scene(args, params):
    clear_scene()
    scene = bpy.context.scene

    total_f = args.frames
    primary_color = params.get("color", [0.0, 0.85, 1.0])       # Cyan
    accent_color = params.get("accent_color", [1.0, 0.45, 0.1])  # Amber
    node_count = params.get("nodes", 45)

    # 1. Dark Void World
    scene.world = bpy.data.worlds.new("VoidWorld")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes["Background"]
    bg_node.inputs["Color"].default_value = (0.005, 0.008, 0.012, 1.0)
    bg_node.inputs["Strength"].default_value = 0.2

    # 2. Materials
    mat_cyan = create_emission_material("MatCyanParticle", primary_color, 5.0)
    mat_amber = create_emission_material("MatAmberParticle", accent_color, 6.0)
    mat_ring = create_emission_material("MatRingAccent", (0.2, 0.4, 0.6), 1.8)

    # 3. Concentric Orbital Rings (Quantum Orbits / Planetary Trajectories)
    ring_radii = [1.8, 3.2, 4.6]
    rings = []
    for idx, r in enumerate(ring_radii):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=r,
            minor_radius=0.018,
            major_segments=64,
            minor_segments=8,
            location=(0, 0, 0)
        )
        ring_obj = bpy.context.active_object
        ring_obj.name = f"OrbitRing_{idx}"
        ring_obj.data.materials.append(mat_ring)
        # Give each ring an inclined orbital tilt
        tilt_x = math.radians(20 * (idx + 1) * (-1 if idx % 2 == 1 else 1))
        tilt_y = math.radians(15 * idx)
        ring_obj.rotation_euler = (tilt_x, tilt_y, 0)

        # Animate rotation around its local axis
        ring_obj.keyframe_insert(data_path="rotation_euler", frame=1)
        ring_obj.rotation_euler = (tilt_x, tilt_y, math.radians(60 * (1 if idx % 2 == 0 else -1)))
        ring_obj.keyframe_insert(data_path="rotation_euler", frame=total_f)
        rings.append(ring_obj)

    # 4. Center Singularity Node
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, segments=32, ring_count=16, location=(0, 0, 0))
    center_core = bpy.context.active_object
    center_core.name = "CenterCore"
    center_core.data.materials.append(mat_amber)

    # 5. Floating Orbital Data Nodes / Particle Swarm
    random.seed(42)
    for i in range(node_count):
        theta = random.uniform(0, 2 * math.pi)
        radius = random.uniform(1.2, 5.5)
        z = random.uniform(-1.5, 1.5)
        size = random.uniform(0.04, 0.11)

        x = radius * math.cos(theta)
        y = radius * math.sin(theta)

        bpy.ops.mesh.primitive_uv_sphere_add(radius=size, segments=12, ring_count=8, location=(x, y, z))
        node_obj = bpy.context.active_object
        node_obj.name = f"ParticleNode_{i}"
        node_obj.data.materials.append(mat_amber if i % 4 == 0 else mat_cyan)

        # Orbit animation: Nodes drift along angular paths
        angular_speed = random.uniform(0.4, 1.2) * (1 if i % 2 == 0 else -1)
        node_obj.keyframe_insert(data_path="location", frame=1)

        new_theta = theta + angular_speed * (total_f / 30.0) * 0.3
        new_x = radius * math.cos(new_theta)
        new_y = radius * math.sin(new_theta)
        new_z = z + math.sin(theta) * 0.2

        node_obj.location = (new_x, new_y, new_z)
        node_obj.keyframe_insert(data_path="location", frame=total_f)

    # 6. Cinematic Floating Camera with Shallow Depth-of-Field Bokeh
    cam_data = bpy.data.cameras.new("OrbitCam")
    cam_data.lens = 50.0  # 50mm Prime
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = center_core
    cam_data.dof.aperture_fstop = 1.4  # Dreamy shallow focus bokeh

    cam_obj = bpy.data.objects.new("OrbitCamObj", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Camera moves from slightly high perspective pushing in towards core
    cam_obj.location = (0.0, -7.0, 2.5)
    cam_obj.rotation_euler = (math.radians(72), 0, 0)
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    cam_obj.location = (1.5, -4.5, 1.2)
    cam_obj.rotation_euler = (math.radians(76), 0, math.radians(-15))
    cam_obj.keyframe_insert(data_path="location", frame=total_f)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=total_f)

    # 7. Render Settings
    temp_dir = Path(args.output).parent / f"frames_orbit_{os.getpid()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    scene.render.engine = args.engine
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.fps = args.fps
    scene.frame_start = 1
    scene.frame_end = total_f

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(temp_dir / "frame_####")

    print(f"🎬 [Blender] Rendering orbital particle frames 1 to {total_f}...")
    bpy.ops.render.render(animation=True)
    print("✅ [Blender] Orbital frames rendered. Compiling via FFmpeg...")

    # 8. FFmpeg MP4 Compilation
    import subprocess
    input_pattern = os.path.join(temp_dir, "frame_%04d.png")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(args.fps),
        "-i", input_pattern,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "medium",
        str(args.output)
    ]
    subp = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if subp.returncode != 0:
        print(f"❌ [FFmpeg] Compilation failed: {subp.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg compile failed: {subp.stderr[-200:]}")

    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"🎬 [Blender+FFmpeg] Orbital render complete -> {args.output}")

def main():
    try:
        args = parse_args()
        params = json.loads(args.params) if args.params else {}
        build_orbital_scene(args, params)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
