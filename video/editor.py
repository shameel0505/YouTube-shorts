import os
import random
import numpy as np
import cv2
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip, ImageClip, VideoClip
)
from moviepy.video.fx.all import crop, resize
from config import (VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
                    CAPTION_FONT_SIZE, CAPTION_STROKE_WIDTH,
                    TEMP_DIR, OUTPUT_DIR, PEXELS_API_KEY,
                    VIDEO_CODEC, AUDIO_CODEC, VIDEO_BITRATE, AUDIO_BITRATE, EXPORT_PRESET, EXPORT_THREADS,
                    CAPTION_HOOK_MULTIPLIER, PILL_PADDING_X, PILL_PADDING_Y, PILL_RADIUS, PILL_COLOR_RGBA,
                    HIGHLIGHT_COLOR, CLIP_SEGMENT_MIN_DUR, CLIP_SEGMENT_MAX_DUR,
                    TITLE_CARD_DURATION, PART_LABEL_FADE_TIME,
                    CLOSING_Q_DURATION, CLOSING_Q_FONT_SIZE, CLOSING_Q_BG_ALPHA, CLOSING_Q_STROKE_WIDTH,
                    PROGRESS_BAR_HEIGHT, PROGRESS_BAR_OPACITY, ASSETS_IMAGES_DIR)

from video.audio_mixer import mix_audio

_FONTS = [
    # 0. Local Project Fonts (Highest Priority)
    os.path.join(os.path.dirname(__file__), "..", "fonts", "Montserrat-ExtraBold.ttf"),
    os.path.join(os.path.dirname(__file__), "..", "fonts", "BebasNeue-Regular.ttf"),

    # 1. Bebas Neue
    "/usr/local/share/fonts/BebasNeue-Regular.ttf",
    "/Library/Fonts/BebasNeue-Regular.ttf",
    "~/Library/Fonts/BebasNeue-Regular.ttf",
    "BebasNeue-Regular.ttf",
    
    # 2. Montserrat ExtraBold
    "/usr/local/share/fonts/Montserrat-ExtraBold.ttf",
    "/Library/Fonts/Montserrat-ExtraBold.ttf",
    "~/Library/Fonts/Montserrat-ExtraBold.ttf",
    "Montserrat-ExtraBold.ttf",
    
    # 3. Anton
    "/usr/local/share/fonts/Anton-Regular.ttf",
    "/Library/Fonts/Anton-Regular.ttf",
    "~/Library/Fonts/Anton-Regular.ttf",
    "Anton-Regular.ttf",
    
    # 4. Poppins Black
    "/usr/local/share/fonts/Poppins-Black.ttf",
    "/Library/Fonts/Poppins-Black.ttf",
    "~/Library/Fonts/Poppins-Black.ttf",
    "Poppins-Black.ttf",
    
    # 5. Impact
    "/usr/local/share/fonts/Impact.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/Library/Fonts/Impact.ttf",
    "Impact.ttf",
    
    # 6. Arial Bold
    "/usr/local/share/fonts/Arial-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "Arial Bold.ttf"
]

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def build_video(
    footage_paths: list[str],
    audio_path: str,
    captions: list[dict],
    audio_duration: float,
    output_filename: str,
    closing_question: str = None,
    fmt: int = 1,
    script_data: dict = None,
    pattern_img_path: str = None
) -> str:
    print("🎞️  Assembling video...")
    
    bg_clip, sfx_triggers = _build_background(footage_paths, audio_duration, fmt)
    
    mixed_audio_path = mix_audio(audio_path, fmt, audio_duration, sfx_triggers)
    final_audio = AudioFileClip(mixed_audio_path)
    
    video = bg_clip.set_audio(final_audio).set_duration(audio_duration)
    
    layers = [video]
    layers.append(_build_gradient_overlay(audio_duration))
    
    if script_data and script_data.get("hook"):
        layers.extend(_build_title_card(script_data["hook"], fmt, script_data.get("part", 1), audio_duration))
        
    caption_clips = _build_caption_clips(captions, audio_duration, fmt, closing_question=closing_question)
    layers.extend(caption_clips)
    
    if fmt == 1:
        img_clip = _build_pattern_interrupt_image(audio_duration, pattern_img_path)
        if img_clip:
            layers.append(img_clip)
        layers.append(_build_format1_heading(audio_duration))
            
    if fmt == 2:
        layers.append(_build_progress_bar(audio_duration))
        
    if closing_question and fmt == 3:
        q_start = max(0.0, audio_duration - CLOSING_Q_DURATION)
        q_dur   = audio_duration - q_start
        layers.extend(_build_closing_question_overlay(closing_question, q_start, q_dur))

    final = CompositeVideoClip(layers)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    final.write_videofile(
        output_path,
        fps=VIDEO_FPS,
        codec=VIDEO_CODEC,
        audio_codec=AUDIO_CODEC,
        bitrate=VIDEO_BITRATE,
        audio_bitrate=AUDIO_BITRATE,
        preset=EXPORT_PRESET,
        threads=EXPORT_THREADS,
        verbose=False,
        logger=None,
    )
    
    # Generate thumbnail
    hook_text = script_data.get("hook", "MIND BLOWING") if script_data else "MIND BLOWING"
    if closing_question and fmt == 3:
        hook_text = script_data.get("dilemma_seed", "WHAT WOULD YOU DO?") if script_data else "WHAT WOULD YOU DO?"
    _generate_thumbnail(output_path, hook_text, fmt)
    
    print(f"✅ Video exported: {output_path}")
    return output_path

def _generate_thumbnail(video_path: str, hook_text: str, fmt: int):
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("⚠️ Failed to extract frame for thumbnail")
            return
            
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        
        if h > w:
            # Vertical video (Shorts): Preserve 100% of Frame 0 with ambient blurred background
            blurred_bg = cv2.resize(frame, (1280, 720))
            blurred_bg = cv2.GaussianBlur(blurred_bg, (51, 51), 0)
            
            scaled_h = 720
            scaled_w = int(w * (720 / h))
            fg_img = cv2.resize(frame, (scaled_w, scaled_h))
            
            x_offset = (1280 - scaled_w) // 2
            blurred_bg[:, x_offset:x_offset+scaled_w] = fg_img
            thumb_img = blurred_bg
        else:
            # Landscape video (Format 5 Widescreen): Resize Frame 0 directly
            thumb_img = cv2.resize(frame, (1280, 720))
            
        pil_img = Image.fromarray(thumb_img)
        out_path = video_path.replace(".mp4", "_thumb.jpg")
        pil_img.save(out_path, quality=95)
        print(f"📸 First-Frame Thumbnail generated: {os.path.basename(out_path)}")
        
    except Exception as e:
        print(f"⚠️ Thumbnail generation failed: {e}")

def _build_background(footage_paths: list[str], duration: float, fmt: int):
    if not footage_paths:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(10, 10, 20), duration=duration), []

    path = footage_paths[0]
    try:
        source_clip = VideoFileClip(path, audio=False)
        
        segments = []
        sfx_triggers = []
        current_time = 0.0
        
        # Cut into 1.5 - 2.5s segments
        while current_time < duration:
            seg_dur = min(duration - current_time, random.uniform(CLIP_SEGMENT_MIN_DUR, CLIP_SEGMENT_MAX_DUR))
            
            max_start = max(0, source_clip.duration - seg_dur)
            start_t = random.uniform(0, max_start)
            
            seg_clip = source_clip.subclip(start_t, start_t + seg_dur)
            seg_clip = _crop_to_vertical(seg_clip)
            
            # Apply color grade
            seg_clip = seg_clip.fl_image(lambda frame: _apply_color_grade(frame, fmt))
            
            segments.append(seg_clip)
            if current_time > 0:
                sfx_triggers.append(current_time)
            
            current_time += seg_dur
            
        bg = concatenate_videoclips(segments, method="compose")
        
        # First frame brightness boost
        def process_first_frame(get_frame, t):
            frame = get_frame(t)
            if t < 0.1:
                # Check mean brightness
                if np.mean(frame) < 40:
                    # Brighten by adding 50 and clipping
                    frame = np.clip(frame.astype(np.int16) + 50, 0, 255).astype(np.uint8)
            return frame
            
        bg = bg.fl(process_first_frame)
        return bg, sfx_triggers
        
    except Exception as e:
        print(f"⚠️  Error building background: {e}")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(10, 10, 20), duration=duration), []

def _apply_color_grade(frame, fmt: int):
    # Convert RGB to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    
    if fmt == 1:
        # Boost saturation
        hsv[:,:,1] = np.clip(hsv[:,:,1] * 1.3, 0, 255)
        rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        # Add orange tint (boost R, slightly boost G)
        rgb = rgb.astype(np.int16)
        rgb[:,:,0] = np.clip(rgb[:,:,0] + 10, 0, 255) # R
        rgb[:,:,1] = np.clip(rgb[:,:,1] + 5, 0, 255)  # G
        rgb = rgb.astype(np.uint8)
        return rgb
        
    elif fmt == 2:
        # Darker, desaturated, blue tint
        hsv[:,:,1] = np.clip(hsv[:,:,1] * 0.6, 0, 255) # desaturate
        hsv[:,:,2] = np.clip(hsv[:,:,2] * 0.7, 0, 255) # darken
        rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        rgb = rgb.astype(np.float32)
        rgb[:,:,2] = rgb[:,:,2] + 15.0 # Blue tint
        
        # Vignette
        rows, cols = rgb.shape[:2]
        kernel_x = cv2.getGaussianKernel(cols, cols/2)
        kernel_y = cv2.getGaussianKernel(rows, rows/2)
        kernel = kernel_y * kernel_x.T
        # Normalize so the center is 1.0 (255)
        mask = 255 * kernel / np.max(kernel)
        mask = cv2.resize(mask, (cols, rows))
        # Ensure mask shape matches rgb shape
        mask = np.dstack([mask]*3).astype(np.float32)
        # Blend
        rgb = cv2.multiply(rgb, mask, scale=1/255.0)
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        return rgb
        
    elif fmt == 3:
        # Neutral, soft blue/green tint
        rgb = frame.astype(np.int16)
        rgb[:,:,1] = np.clip(rgb[:,:,1] + 5, 0, 255)  # G
        rgb[:,:,2] = np.clip(rgb[:,:,2] + 10, 0, 255) # B
        rgb = rgb.astype(np.uint8)
        return rgb
        
    return frame

def _build_gradient_overlay(duration: float):
    grad = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grad)
    grad_start = int(VIDEO_HEIGHT * 0.52)
    for y in range(grad_start, VIDEO_HEIGHT):
        alpha = int(200 * (y - grad_start) / (VIDEO_HEIGHT - grad_start))
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(0, 0, 0, alpha))
    return ImageClip(np.array(grad)).set_duration(duration)

def _crop_to_vertical(clip):
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    w, h = clip.size
    clip_ratio = w / h
    if clip_ratio > target_ratio:
        new_w = int(h * target_ratio)
        clip = crop(clip, width=new_w, height=h, x_center=w/2, y_center=h/2)
    elif clip_ratio < target_ratio:
        new_h = int(w / target_ratio)
        clip = crop(clip, width=w, height=new_h, x_center=w/2, y_center=h/2)
    return resize(clip, newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))

def _build_title_card(hook: str, fmt: int, part: int, video_duration: float) -> list:
    layers = []
    
    text = hook.upper()
    font_size = int(CAPTION_FONT_SIZE * 0.95)
    font = _load_font(font_size)
    
    probe = Image.new("RGBA", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    
    # Measure and split into lines
    max_w = VIDEO_WIDTH - 100
    words = text.split()
    lines = []
    current_line = []
    for w in words:
        if "\n" in w:
            parts = w.split("\n")
            current_line.append(parts[0])
            lines.append(" ".join(current_line))
            current_line = [parts[1]] if len(parts) > 1 else []
            continue
            
        current_line.append(w)
        line_str = " ".join(current_line)
        bbox = probe_draw.textbbox((0, 0), line_str, font=font)
        if (bbox[2] - bbox[0]) > max_w:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [w]
    if current_line:
        lines.append(" ".join(current_line))
        
    multiline_text = "\n".join(lines)
    bbox = probe_draw.multiline_textbbox((0, 0), multiline_text, font=font, spacing=15)
    text_h = bbox[3] - bbox[1]
    
    canvas_w = VIDEO_WIDTH
    canvas_h = text_h + 150
    if fmt == 2:
        canvas_h += 80
    
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx = canvas_w // 2
    cy = 50
    
    # Draw drop shadow instead of a background box
    shadow_offset = 6
    draw.multiline_text(
        (cx + shadow_offset, cy + shadow_offset),
        multiline_text,
        font=font,
        fill=(0, 0, 0, 200),
        align="center",
        spacing=15,
        anchor="ma"
    )
    
    # Draw main text
    draw.multiline_text(
        (cx, cy),
        multiline_text,
        font=font,
        fill="white",
        stroke_width=CAPTION_STROKE_WIDTH + 2,
        stroke_fill="black",
        align="center",
        spacing=15,
        anchor="ma"
    )
    
    if fmt == 2:
        # Draw PART NO underneath for Format 2
        part_text = f"PART {part}"
        font_sm = _load_font(int(CAPTION_FONT_SIZE * 0.7))
        
        # Drop shadow for part
        draw.text(
            (cx + 4, cy + text_h + 30 + 4),
            part_text,
            font=font_sm,
            fill=(0, 0, 0, 200),
            anchor="ma"
        )
        
        # Main part text
        draw.text(
            (cx, cy + text_h + 30),
            part_text,
            font=font_sm,
            fill=HIGHLIGHT_COLOR.get(2, "#FF2222"),
            stroke_width=CAPTION_STROKE_WIDTH,
            stroke_fill="black",
            anchor="ma"
        )
    
    np_img = np.array(img)
    text_clip = ImageClip(np_img).set_start(0).set_duration(video_duration).set_position(("center", 180))
    layers.append(text_clip)
        
    return layers

def _build_caption_clips(captions: list[dict], video_clip, fmt: int, closing_question: str = None) -> list:
    if not captions:
        return []
        
    vw, vh = video_clip.size if hasattr(video_clip, 'size') else (VIDEO_WIDTH, VIDEO_HEIGHT)

    # Position in the lower portion (around 80%)
    center_y = int(vh * 0.80)
    font = _load_font(CAPTION_FONT_SIZE)

    closing_start = (video_clip.duration - CLOSING_Q_DURATION) if closing_question and fmt == 3 else video_clip.duration
    
    clips = []
    for chunk in captions:
        if chunk["start"] >= video_clip.duration:
            continue
        if chunk["start"] >= closing_start:
            continue 

        words = chunk["words"]
        for active_idx, active_word in enumerate(words):
            start = active_word["start"]
            if start >= video_clip.duration or start >= closing_start:
                continue

            end = words[active_idx + 1]["start"] if active_idx < len(words) - 1 else chunk["end"]
            end = min(end, video_clip.duration, closing_start)
            dur = end - start
            if dur <= 0:
                continue

            img_clip = _render_word_frame(words, active_idx, font, center_y, vw, fmt)
            if img_clip:
                clips.append(img_clip.set_start(start).set_duration(dur))

    return clips

def _render_word_frame(words, active_idx, font, center_y, vw, fmt):
    probe = Image.new("RGBA", (1, 1))
    probe_draw = ImageDraw.Draw(probe)

    texts = [w["text"].upper() for w in words]
    widths = [probe_draw.textbbox((0, 0), t, font=font)[2] - probe_draw.textbbox((0, 0), t, font=font)[0] for t in texts]

    # Elegant cinematic letter/word tracking
    gap = 20
    max_allowed = vw - 80

    # Line wrapping algorithm (Font size is strictly locked!)
    lines = []
    current_line_words = []
    current_line_w = 0
    
    for i, (w_text, w_px) in enumerate(zip(texts, widths)):
        if current_line_w + w_px + gap > max_allowed and current_line_words:
            lines.append({"words": current_line_words, "width": current_line_w - gap})
            current_line_words = []
            current_line_w = 0
            
        current_line_words.append((i, w_text, w_px))
        current_line_w += w_px + gap
        
    if current_line_words:
        lines.append({"words": current_line_words, "width": current_line_w - gap})

    sample_bbox = probe_draw.textbbox((0, 0), "Ay", font=font)
    text_h = sample_bbox[3] - sample_bbox[1]
    line_spacing = int(text_h * 1.2)

    total_h = line_spacing * len(lines)
    canvas_w = vw
    
    shadow_offset = 6
    blur_radius = 8
    canvas_h = total_h + shadow_offset + blur_radius * 2 + 40

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    from PIL import ImageFilter
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)

    start_y = (canvas_h - total_h) // 2

    # Draw Drop Shadows
    y = start_y
    for line in lines:
        x = (canvas_w - line["width"]) // 2
        for _, w_text, w_px in line["words"]:
            shadow_draw.text((x + shadow_offset, y + shadow_offset), w_text, font=font, fill=(0, 0, 0, 200))
            x += w_px + gap
        y += line_spacing

    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(blur_radius))
    img.alpha_composite(shadow_img)

    # Draw Text
    y = start_y
    modern_cyan = (0, 229, 255, 255) # Modern 2026 High-Retention Cyan

    for line in lines:
        x = (canvas_w - line["width"]) // 2
        for orig_idx, w_text, w_px in line["words"]:
            color = modern_cyan if orig_idx == active_idx else (255, 255, 255, 255)
            draw.text((x, y), w_text, font=font, fill=color)
            x += w_px + gap
        y += line_spacing

    np_img = np.array(img)
    top_y = center_y - canvas_h // 2
    return ImageClip(np_img).set_position(("center", top_y))

def _build_closing_question_overlay(question: str, start: float, duration: float) -> list:
    bg_img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, CLOSING_Q_BG_ALPHA))
    bg_clip = ImageClip(np.array(bg_img)).set_start(start).set_duration(duration)

    q_text = question.upper()
    call_to_action = "LET ME KNOW IN THE COMMENTS"

    probe = Image.new("RGBA", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    
    # Split into lines of no more than 12 words each
    words = q_text.split()
    lines = []
    for i in range(0, len(words), 12):
        lines.append(" ".join(words[i:i+12]))
        
    lines.append("")
    lines.append(call_to_action)

    # Font reduction logic
    font_size = 72
    max_w = VIDEO_WIDTH - 120
    
    while font_size >= 24:
        font = _load_font(font_size)
        too_wide = False
        for line in lines:
            if not line:
                continue
            bbox = probe_draw.textbbox((0, 0), line, font=font)
            if (bbox[2] - bbox[0]) > max_w:
                too_wide = True
                break
        if too_wide:
            font_size -= 4
        else:
            break

    font = _load_font(font_size)
    line_spacing = 24
    
    # Truncate with ellipsis if still too wide (fallback)
    final_lines = []
    for line in lines:
        if not line:
            final_lines.append("")
            continue
        bbox = probe_draw.textbbox((0, 0), line, font=font)
        if (bbox[2] - bbox[0]) > max_w:
            while len(line) > 3:
                line = line[:-1]
                bbox = probe_draw.textbbox((0, 0), line + "...", font=font)
                if (bbox[2] - bbox[0]) <= max_w:
                    line += "..."
                    break
        final_lines.append(line)

    # Measure total height
    total_text_height = 0
    for line in final_lines:
        if not line:
            total_text_height += (font_size // 2) + line_spacing
            continue
        bbox = probe_draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        total_text_height += h + line_spacing
    total_text_height -= line_spacing # Remove trailing spacing

    # Padding
    pad_x = 40
    pad_y = 24
    
    # Find actual max width used by text
    actual_max_w = 0
    for line in final_lines:
        if not line: continue
        bbox = probe_draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        if w > actual_max_w:
            actual_max_w = w
            
    box_w = actual_max_w + (pad_x * 2)
    box_h = total_text_height + (pad_y * 2)

    # Center in lower 40% of the screen.
    # Lower 40% means from y = 0.6 * VIDEO_HEIGHT to VIDEO_HEIGHT.
    # Center of lower 40% is y = 0.8 * VIDEO_HEIGHT
    center_y = int(VIDEO_HEIGHT * 0.8)
    
    # Boundary checks for the box
    box_y0 = center_y - (box_h // 2)
    box_y1 = box_y0 + box_h
    if box_y1 > VIDEO_HEIGHT - 20:
        box_y1 = VIDEO_HEIGHT - 20
        box_y0 = box_y1 - box_h
    if box_y0 < 0:
        box_y0 = 20

    box_x0 = (VIDEO_WIDTH - box_w) // 2
    box_x1 = box_x0 + box_w

    # Draw canvas
    canvas = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Draw semi-transparent dark rounded rectangle
    draw.rounded_rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        radius=20,
        fill=(0, 0, 0, 200)
    )

    # Draw text lines
    current_y = box_y0 + pad_y
    for i, line in enumerate(final_lines):
        if not line:
            current_y += (font_size // 2) + line_spacing
            continue
            
        bbox = probe_draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (VIDEO_WIDTH - w) // 2
        
        # Color the call to action differently
        if i == len(final_lines) - 1:
            fill_color = HIGHLIGHT_COLOR.get(3, "#66CCFF")
        else:
            fill_color = "white"
            
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=fill_color,
            stroke_width=4,
            stroke_fill="black"
        )
        current_y += h + line_spacing

    np_canvas = np.array(canvas)
    text_clip = ImageClip(np_canvas).set_start(start).set_duration(duration)

    return [bg_clip, text_clip]

def _build_pattern_interrupt_image(video_duration: float, img_path: str = None):
    # Format 1 only: At midpoint, insert 1.5s image clip with Ken Burns
    if not img_path or not os.path.exists(img_path):
        return None
    
    midpoint = video_duration / 2.0
    dur = 1.5
    
    try:
        # Resize height and set placement between top title and bottom captions
        img_clip = ImageClip(img_path).set_duration(dur)
        img_clip = img_clip.resize(height=550)
        
        if img_clip.w > VIDEO_WIDTH - 60:
            x_center = img_clip.w / 2
            y_center = img_clip.h / 2
            img_clip = crop(img_clip, width=VIDEO_WIDTH - 60, height=img_clip.h, x_center=x_center, y_center=y_center)
            
        img_clip = img_clip.margin(left=15, right=15, top=15, bottom=15, color=(255, 255, 255))
        img_clip = img_clip.set_position(("center", 450)) # Anchored at y=450
        
        # Ken Burns zoom effect
        def zoom(get_frame, t):
            frame = get_frame(t)
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
                
            scale = 1.0 + (0.08 * (t / dur))
            
            h, w = frame.shape[:2]
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h))
            
            x = (new_w - w) // 2
            y = (new_h - h) // 2
            cropped = resized[y:y+h, x:x+w]
            
            cropped = cropped.astype(np.uint8)
            overlay = np.zeros_like(cropped, dtype=np.uint8)
            cropped = cv2.addWeighted(cropped, 0.6, overlay, 0.4, 0)
            
            return cropped
            
        return img_clip.fl(zoom).set_start(midpoint)
        
    except Exception as e:
        print(f"   ⚠️ Failed to build pattern interrupt: {e}")
        return None

def _build_progress_bar(duration: float):
    # Format 2 only: Thin white bar fills left-to-right at bottom
    def make_frame(t):
        frame = np.zeros((PROGRESS_BAR_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        progress = min(1.0, max(0.0, t / duration))
        width = int(VIDEO_WIDTH * progress)
        if width > 0:
            frame[:, :width] = (255, 255, 255)
        return frame
        
    def make_mask(t):
        mask = np.zeros((PROGRESS_BAR_HEIGHT, VIDEO_WIDTH), dtype=np.float32)
        progress = min(1.0, max(0.0, t / duration))
        width = int(VIDEO_WIDTH * progress)
        if width > 0:
            mask[:, :width] = PROGRESS_BAR_OPACITY
        return mask
        
    clip = VideoClip(make_frame, duration=duration)
    mask_clip = VideoClip(make_mask, duration=duration, ismask=True)
    clip = clip.set_mask(mask_clip)
    
    return clip.set_position(("center", "bottom"))

def _build_format1_heading(duration: float):
    # Format 1 only: "DID YOU KNOW?" static text at the top
    text = "DID YOU KNOW?"
    font_size = 80
    font = _load_font(font_size)
    
    probe = Image.new("RGBA", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    canvas = Image.new("RGBA", (VIDEO_WIDTH, h + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Yellow highlighted text
    draw.text(
        ((VIDEO_WIDTH - w) // 2, 20),
        text,
        font=font,
        fill="#FFD700",
        stroke_width=6,
        stroke_fill="black"
    )
    
    np_canvas = np.array(canvas)
    clip = ImageClip(np_canvas).set_start(0).set_duration(duration)
    return clip.set_position(("center", 150))
