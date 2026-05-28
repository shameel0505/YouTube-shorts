FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libmagickwand-dev \
    fonts-liberation \
    fonts-dejavu-core \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick security policy to allow text rendering (required for MoviePy TextClip)
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' \
    /etc/ImageMagick-6/policy.xml 2>/dev/null || true
RUN sed -i 's/rights="none" pattern="@\*" /rights="read|write" pattern="@*" /' \
    /etc/ImageMagick-6/policy.xml 2>/dev/null || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper base model at build time so first run is fast
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

COPY . .

RUN mkdir -p output temp logs assets

CMD ["python", "main.py", "run"]
