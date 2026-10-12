#!/bin/bash
# setup_gflow.sh - Installs gflow-cli and authenticates Google Flow

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Setting up gflow-cli for Google Veo/Imagen..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Ensure we are in the project root
cd "$(dirname "$0")/.." || exit

# Check if venv exists and activate it
if [ -d "venv" ]; then
    echo "[1/3] Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Error: Virtual environment 'venv' not found. Please create one first."
    exit 1
fi

echo "[2/3] Installing gflow-cli and Playwright dependencies..."
pip install gflow-cli
playwright install chromium

echo ""
echo "[3/3] Launching Authentication..."
echo "⚠️ IMPORTANT: A Chromium browser window will open shortly."
echo "Please sign in to your Google Account that holds the Google AI Pro subscription."
echo "Wait for the Google Flow dashboard to load fully, then close the browser to save the session."
echo ""
read -p "Press [Enter] to launch the browser..."

gflow auth login --profile youtube --browser internal

echo ""
echo "Verifying authentication..."
gflow auth status --profile youtube

echo ""
echo "✅ Setup complete! You can now run the experimental test scripts."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
