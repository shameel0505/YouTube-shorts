"""
Blender 3D Procedural Schematic Wireframe / Exploding CAD Template.
Creates a technical blueprint / mechanical disassembly sequence with
wireframe emission shaders, 3D callout annotations, and a cinematic orbital camera.
Compatible with Blender 4.x / 5.x LTS.
"""
import sys
import os
import argparse
import json
import math
from pathlib import Path
import bpy

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Render 3D Schematic Wireframe Exploded Assembly")
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

def create_wireframe_material(name: str, base_color: tuple, edge_color: tuple, emission_strength: float = 3.5):
    """Creates a technical wireframe + metallic shader node tree."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output node
    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (600, 0)

    # Mix Shader
    mix = nodes.new(type="ShaderNodeMixShader")
    mix.location = (400, 0)

    # Base Principled BSDF (Dark metallic tech chassis)
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (100, -100)
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.85
    bsdf.inputs["Roughness"].default_value = 0.35

    # Wireframe Emission Node
    emission = nodes.new(type="ShaderNodeEmission")
    emission.location = (100, 100)
    emission.inputs["Color"].default_value = (*edge_color, 1.0)
    emission.inputs["Strength"].default_value = emission_strength

    # Wireframe factor
    wire = nodes.new(type="ShaderNodeWireframe")
    wire.location = (-100, 100)
    wire.inputs["Size"].default_value = 0.015

    # Connect
    links.new(wire.outputs["Fac"], mix.inputs["Fac"])
    links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    return mat

def create_glowing_core_material(name: str, core_color: tuple):
    """Creates an inner pulsating emissive core material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (400, 0)

    emission = nodes.new(type="ShaderNodeEmission")
    emission.location = (150, 0)
    emission.inputs["Color"].default_value = (*core_color, 1.0)
    emission.inputs["Strength"].default_value = 5.0

    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat

def build_schematic_scene(args, params):
    clear_scene()
    scene = bpy.context.scene

    # Parse parameters
    subject_title = params.get("title", "SYSTEM SCHEMATIC").upper()
    callout_1 = params.get("callout_top", "UPPER REFLECTOR [BE-9]").upper()
    callout_2 = params.get("callout_core", "ACTIVE CORE [PU-239]").upper()
    callout_3 = params.get("callout_base", "LOWER CRADLE [SUB-CRITICAL]").upper()

    cyan_accent = params.get("accent_color", [0.0, 0.85, 1.0])      # Technical cyan
    amber_accent = params.get("core_color", [1.0, 0.42, 0.05])       # Supercritical amber
    chassis_color = params.get("chassis_color", [0.03, 0.04, 0.05])  # Dark titanium

    # 1. World & Lighting
    scene.world = bpy.data.worlds.new("TechBlueprintWorld")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes["Background"]
    bg_node.inputs["Color"].default_value = (0.012, 0.015, 0.02, 1.0)
    bg_node.inputs["Strength"].default_value = 0.4

    # Key light (Cool blue rim)
    key_light_data = bpy.data.lights.new("KeyRim", type="AREA")
    key_light_data.energy = 450.0
    key_light_data.size = 5.0
    key_light_data.color = (0.7, 0.85, 1.0)
    key_light = bpy.data.objects.new("KeyRimObj", key_light_data)
    key_light.location = (4.0, -4.0, 5.0)
    scene.collection.objects.link(key_light)

    # Fill light (Subtle warm underglow)
    fill_light_data = bpy.data.lights.new("FillUnder", type="POINT")
    fill_light_data.energy = 180.0
    fill_light_data.color = (1.0, 0.6, 0.3)
    fill_light = bpy.data.objects.new("FillUnderObj", fill_light_data)
    fill_light.location = (-3.0, 3.0, -2.5)
    scene.collection.objects.link(fill_light)

    # 2. Materials
    mat_shell = create_wireframe_material("MatShell", chassis_color, cyan_accent, 3.0)
    mat_core = create_glowing_core_material("MatCore", amber_accent)
    mat_ring = create_wireframe_material("MatRing", chassis_color, (0.4, 0.6, 0.9), 2.0)

    # 3. Create Exploding CAD Assembly Components
    # Component A: Inner Core Sphere (Plutonium Sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.75, segments=32, ring_count=24, location=(0, 0, 0))
    core_obj = bpy.context.active_object
    core_obj.name = "Assembly_Core"
    core_obj.data.materials.append(mat_core)

    # Component B: Upper Hemisphere (Beryllium Shell)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, segments=32, ring_count=24, location=(0, 0, 0))
    upper_shell = bpy.context.active_object
    upper_shell.name = "Assembly_UpperShell"
    # Clip lower half in edit mode / scale or slice
    upper_shell.data.materials.append(mat_shell)

    # Component C: Lower Cradle / Ring Base
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.5,
        minor_radius=0.18,
        major_segments=36,
        minor_segments=16,
        location=(0, 0, 0)
    )
    cradle_obj = bpy.context.active_object
    cradle_obj.name = "Assembly_Cradle"
    cradle_obj.data.materials.append(mat_ring)

    # Component D: Equatorial Spacer Calipers
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=3.4, vertices=16, location=(0, 0, 0))
    spacer_obj = bpy.context.active_object
    spacer_obj.name = "Assembly_SpacerBar"
    spacer_obj.rotation_euler = (0, math.radians(90), 0)
    spacer_obj.data.materials.append(mat_shell)

    # 4. Blueprint Measurement Floor Grid
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=24, size=14.0, location=(0, 0, -2.5))
    grid_floor = bpy.context.active_object
    grid_floor.name = "FloorGrid"
    grid_mat = create_wireframe_material("MatGrid", (0.01, 0.012, 0.015), (0.1, 0.3, 0.5), 1.2)
    grid_floor.data.materials.append(grid_mat)

    # 5. Exploded Assembly Keyframe Animation
    # Phase 1: Frames 1 - 25 (Closed / Assembled)
    # Phase 2: Frames 25 - 65 (Exploding separation outwards)
    # Phase 3: Frames 65 - 120 (Floating exploded state with slow rotation)

    total_f = args.frames
    f_start_explode = int(total_f * 0.18)
    f_peak_explode = int(total_f * 0.55)

    # Animate Upper Shell (Lifts up on Z axis)
    upper_shell.location = (0, 0, 0.15)
    upper_shell.keyframe_insert(data_path="location", frame=1)
    upper_shell.keyframe_insert(data_path="location", frame=f_start_explode)

    upper_shell.location = (0, 0, 1.6)
    upper_shell.keyframe_insert(data_path="location", frame=f_peak_explode)
    upper_shell.location = (0, 0, 1.7)
    upper_shell.keyframe_insert(data_path="location", frame=total_f)

    # Animate Lower Cradle (Drops down on Z axis)
    cradle_obj.location = (0, 0, -0.15)
    cradle_obj.keyframe_insert(data_path="location", frame=1)
    cradle_obj.keyframe_insert(data_path="location", frame=f_start_explode)

    cradle_obj.location = (0, 0, -1.3)
    cradle_obj.keyframe_insert(data_path="location", frame=f_peak_explode)
    cradle_obj.location = (0, 0, -1.4)
    cradle_obj.keyframe_insert(data_path="location", frame=total_f)

    # Animate Spacer (Slides outward along X axis)
    spacer_obj.location = (0, 0, 0)
    spacer_obj.keyframe_insert(data_path="location", frame=1)
    spacer_obj.keyframe_insert(data_path="location", frame=f_start_explode)

    spacer_obj.location = (1.2, 0, 0.2)
    spacer_obj.keyframe_insert(data_path="location", frame=f_peak_explode)
    spacer_obj.location = (1.35, 0, 0.25)
    spacer_obj.keyframe_insert(data_path="location", frame=total_f)

    # Core slight hover & pulse
    core_obj.location = (0, 0, 0)
    core_obj.keyframe_insert(data_path="location", frame=1)
    core_obj.location = (0, 0, 0.1)
    core_obj.keyframe_insert(data_path="location", frame=int(total_f * 0.6))
    core_obj.location = (0, 0, -0.05)
    core_obj.keyframe_insert(data_path="location", frame=total_f)

    # 6. Technical Text Annotations (3D Billboards)
    def add_callout(text: str, target_loc: tuple, offset_loc: tuple, name: str):
        bpy.ops.object.text_add(location=offset_loc)
        txt = bpy.context.active_object
        txt.name = name
        txt.data.body = text
        txt.data.size = 0.16
        txt.data.extrude = 0.015
        txt.data.align_x = "LEFT"
        txt.data.materials.append(mat_shell)
        # Face camera
        txt.rotation_euler = (math.radians(72), 0, math.radians(-30))
        return txt

    add_callout(f"// {callout_1}", (0, 0, 1.6), (0.8, -1.2, 1.8), "Callout_Top")
    add_callout(f"// {callout_2}", (0, 0, 0.0), (1.1, -1.0, 0.1), "Callout_Core")
    add_callout(f"// {callout_3}", (0, 0, -1.3), (1.2, -1.0, -1.3), "Callout_Base")

    # 7. Cinematic Camera & Orbit Animation
    cam_data = bpy.data.cameras.new("SchematicCam")
    cam_data.lens = 70.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = core_obj
    cam_data.dof.aperture_fstop = 2.4

    cam_obj = bpy.data.objects.new("SchematicCamObj", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Camera moves in a smooth orbital arc around the assembly
    # Start: 3/4 isometric angle
    cam_dist = 6.2
    angle_start = math.radians(-35)
    angle_end = math.radians(15)

    cam_obj.location = (cam_dist * math.sin(angle_start), -cam_dist * math.cos(angle_start), 2.2)
    cam_obj.rotation_euler = (math.radians(74), 0, math.radians(-25))
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    cam_obj.location = (cam_dist * math.sin(angle_end), -cam_dist * math.cos(angle_end), 1.6)
    cam_obj.rotation_euler = (math.radians(78), 0, math.radians(10))
    cam_obj.keyframe_insert(data_path="location", frame=total_f)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=total_f)

    # 8. Render Settings
    temp_dir = Path(args.output).parent / f"frames_schematic_{os.getpid()}"
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

    print(f"🎬 [Blender] Rendering schematic frames 1 to {total_f}...")
    bpy.ops.render.render(animation=True)
    print("✅ [Blender] Schematic frames rendered. Compiling via FFmpeg...")

    # 9. FFmpeg MP4 Compilation
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
    print(f"🎬 [Blender+FFmpeg] Schematic render complete -> {args.output}")

def main():
    try:
        args = parse_args()
        params = json.loads(args.params) if args.params else {}
        build_schematic_scene(args, params)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
