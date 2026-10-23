"""
Procedural 3D Kinetic Title Template for Blender.
Executed inside Blender via:
  blender --background --factory-startup --python kinetic_title.py -- --output <path> --params <json>
"""
import sys
import os
import json
import math
import argparse

try:
    import bpy
    import mathutils
except ImportError:
    pass  # Not running inside Blender

def parse_args():
    # Everything after '--' is for the script
    argv = sys.argv
    if "--" in argv:
        args_to_parse = argv[argv.index("--") + 1:]
    else:
        args_to_parse = []

    parser = argparse.ArgumentParser(description="Blender Kinetic Title Generator")
    parser.add_argument("--output", required=True, help="Output mp4 path")
    parser.add_argument("--params", default="{}", help="JSON string of parameters")
    parser.add_argument("--frames", type=int, default=90, help="Total frames")
    parser.add_argument("--fps", type=int, default=30, help="Frame rate")
    parser.add_argument("--width", type=int, default=1920, help="Resolution width")
    parser.add_argument("--height", type=int, default=1080, help="Resolution height")
    parser.add_argument("--engine", default="BLENDER_EEVEE_NEXT", help="Render engine")
    return parser.parse_args(args_to_parse)

def build_kinetic_title_scene(args, params):
    # 1. Clean existing scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 2. Render Settings
    scene.render.engine = args.engine if hasattr(bpy.types.RenderSettings, args.engine) else "BLENDER_EEVEE"
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.fps = args.fps
    scene.frame_start = 1
    scene.frame_end = args.frames

    # Image sequence output configuration (PNG lossless)
    temp_frames_dir = os.path.join(os.path.dirname(args.output), "blender_frames_" + os.path.basename(args.output).replace(".", "_"))
    os.makedirs(temp_frames_dir, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 15
    scene.render.filepath = os.path.join(temp_frames_dir, "frame_")

    # Enable Motion Blur if available
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = True

    # 3. Create World / Dark Cinematic Background
    world = bpy.data.worlds.new("CinematicWorld")
    scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.015, 0.02, 0.025, 1.0)
        bg_node.inputs["Strength"].default_value = 0.5

    # 4. Text Content & Subtitle
    title_text = params.get("text", "THE UNKNOWN ANOMALY").upper()
    subtitle_text = params.get("subtitle", "EVIDENCE ARCHIVE // CLASSIFIED").upper()

    # Create 3D Title Object
    title_curve = bpy.data.curves.new(type="FONT", name="TitleCurve")
    title_curve.body = title_text
    title_curve.align_x = "CENTER"
    title_curve.align_y = "CENTER"
    title_curve.extrude = 0.08
    title_curve.bevel_depth = 0.015
    title_curve.bevel_resolution = 4

    title_obj = bpy.data.objects.new("TitleText", title_curve)
    scene.collection.objects.link(title_obj)
    title_obj.location = (0, 0, 0.2)

    # Title Material (Metallic Brushed Gunmetal / Titanium)
    title_mat = bpy.data.materials.new(name="TitleMaterial")
    title_mat.use_nodes = True
    nodes = title_mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.88, 0.92, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.90
        bsdf.inputs["Roughness"].default_value = 0.20
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.8
    title_obj.data.materials.append(title_mat)

    # Subtitle Object (Smaller, High-Tech Amber/Cyan Accent)
    if subtitle_text:
        sub_curve = bpy.data.curves.new(type="FONT", name="SubtitleCurve")
        sub_curve.body = subtitle_text
        sub_curve.align_x = "CENTER"
        sub_curve.align_y = "CENTER"
        sub_curve.size = 0.35
        sub_curve.extrude = 0.02
        sub_curve.bevel_depth = 0.005

        sub_obj = bpy.data.objects.new("SubtitleText", sub_curve)
        scene.collection.objects.link(sub_obj)
        sub_obj.location = (0, 0, -0.6)

        sub_mat = bpy.data.materials.new(name="SubtitleMaterial")
        sub_mat.use_nodes = True
        sub_bsdf = sub_mat.node_tree.nodes.get("Principled BSDF")
        if sub_bsdf:
            # High-tech warm amber
            sub_bsdf.inputs["Base Color"].default_value = (1.0, 0.70, 0.15, 1.0)
            sub_bsdf.inputs["Emission Color"].default_value = (1.0, 0.70, 0.15, 1.0)
            if "Emission Strength" in sub_bsdf.inputs:
                sub_bsdf.inputs["Emission Strength"].default_value = 1.5
        sub_obj.data.materials.append(sub_mat)

    # 5. Studio Lighting Rig
    # Key Light (Warm 3200K spotlight)
    key_light_data = bpy.data.lights.new(name="KeySpot", type="SPOT")
    key_light_data.energy = 800.0
    key_light_data.spot_size = math.radians(45)
    key_light_data.spot_blend = 0.4
    key_light_data.color = (1.0, 0.92, 0.80)  # Warm 3200K
    key_light = bpy.data.objects.new(name="KeySpot", object_data=key_light_data)
    scene.collection.objects.link(key_light)
    key_light.location = (2.5, -4.0, 3.5)
    key_light.rotation_euler = (math.radians(45), 0, math.radians(25))

    # Rim / Edge Backlight (Cool Electric Cyan 6500K)
    rim_light_data = bpy.data.lights.new(name="RimArea", type="AREA")
    rim_light_data.energy = 1200.0
    rim_light_data.size = 4.0
    rim_light_data.color = (0.2, 0.7, 1.0)  # Electric cyan
    rim_light = bpy.data.objects.new(name="RimArea", object_data=rim_light_data)
    scene.collection.objects.link(rim_light)
    rim_light.location = (-3.0, 3.0, -1.0)
    rim_light.rotation_euler = (math.radians(-45), 0, math.radians(-135))

    # 6. Camera Rig with Cinematic Depth of Field
    cam_data = bpy.data.cameras.new("CinemaCamera")
    cam_data.lens = 65.0  # 65mm Portrait Prime Lens
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = title_obj
    cam_data.dof.aperture_fstop = 2.8  # Organic depth-of-field blur

    cam_obj = bpy.data.objects.new("CinemaCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 7. Cinematic Camera Animation (Linear Dolly Push-In with Subtle Dutch Tilt)
    # Start: Frame 1
    cam_obj.location = (0.0, -6.5, 0.3)
    cam_obj.rotation_euler = (math.radians(88), 0, math.radians(2.0))
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    # End: Frame args.frames
    cam_obj.location = (0.0, -4.8, 0.1)
    cam_obj.rotation_euler = (math.radians(90), 0, math.radians(0.0))
    cam_obj.keyframe_insert(data_path="location", frame=args.frames)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=args.frames)

    # Smooth Bezier Interpolation (Safe for Blender 5.x action data-block)
    if cam_obj.animation_data and cam_obj.animation_data.action:
        action = cam_obj.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves:
            for fcurve in fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = "BEZIER"

    # 8. Render Scene
    print(f"🎬 [Blender] Rendering frames 1 to {args.frames}...")
    bpy.ops.render.render(animation=True)
    print("✅ [Blender] Animation frame render finished. Compiling with FFmpeg...")

    # 9. Compile PNG sequence into final MP4 using native FFmpeg
    import subprocess
    input_pattern = os.path.join(temp_frames_dir, "frame_%04d.png")
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

    # Clean up temporary frames
    import shutil
    shutil.rmtree(temp_frames_dir, ignore_errors=True)
    print(f"🎬 [Blender+FFmpeg] Render compiled successfully -> {args.output}")

def main():
    args = parse_args()
    params = json.loads(args.params) if args.params else {}
    build_kinetic_title_scene(args, params)

if __name__ == "__main__":
    main()
