FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ffmpeg (needed for moviepy) and playwright
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright requires installing browsers
RUN playwright install chromium
RUN playwright install-deps

COPY . .

# Run the health check server which wraps the bot
CMD ["python", "server.py"]
