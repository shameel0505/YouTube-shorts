#!/bin/bash
mkdir -p gameplay

URLS=(
    "https://www.youtube.com/watch?v=s600FYgI5-s"
    "https://www.youtube.com/watch?v=xKRNDalWE-E"
    "https://www.youtube.com/watch?v=Y-C5Ks3g0Go"
    "https://www.youtube.com/watch?v=sDynZM5ppBc"
    "https://www.youtube.com/watch?v=JvI-02Q69ms"
    "https://www.youtube.com/watch?v=9sbhj1cm9Pc"
    "https://www.youtube.com/watch?v=e1emEay0ink"
    "https://www.youtube.com/watch?v=P3b3AidldmA"
    "https://www.youtube.com/watch?v=wr868MUcTag"
    "https://www.youtube.com/watch?v=zywXZavKy3k"
    "https://www.youtube.com/watch?v=1HzzlGGhW4M"
)

for URL in "${URLS[@]}"; do
    echo "Downloading $URL..."
    yt-dlp -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o 'gameplay/%(title)s.%(ext)s' "$URL"
done

echo "✅ All gameplay footage downloaded!"
