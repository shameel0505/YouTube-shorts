#!/bin/bash

# Navigate to experiments folder
cd /Users/shameel/Desktop/youtube/experiments

echo "=== FFmpeg Quality Test ==="
if [ ! -f "source_lowres.mp4" ]; then
    echo "ERROR: Please copy one of your raw, un-upscaled NotebookLM videos into this folder and name it 'source_lowres.mp4'"
    exit 1
fi

echo "Upscaling using OLD method (ultrafast preset)..."
# Old method from notebooklm_footage.py
ffmpeg -y -i source_lowres.mp4 -vf scale=1080:1920:flags=lanczos -c:v libx264 -preset ultrafast -crf 18 old_method.mp4 -hide_banner -loglevel error

echo "Upscaling using NEW method (medium preset)..."
# New method from notebooklm_footage.py
ffmpeg -y -i source_lowres.mp4 -vf scale=1080:1920:flags=lanczos -c:v libx264 -preset medium -crf 18 new_method.mp4 -hide_banner -loglevel error

echo ""
echo "=== File Size Comparison ==="
ls -lh source_lowres.mp4 old_method.mp4 new_method.mp4

echo ""
echo "Videos are ready in the experiments folder! You can play old_method.mp4 and new_method.mp4 side-by-side."
