#!/bin/bash
set -e

echo "🚀 Deploying NotebookLM Auth Ping to Google Cloud Run..."

# Go to the experiments folder so it becomes the build context, bypassing the root .gitignore!
cd "$(dirname "$0")"

if [ ! -f "gcp_storage_state.json" ]; then
    echo "❌ ERROR: gcp_storage_state.json not found in the experiments folder!"
    exit 1
fi

if [ ! -f "../.env" ]; then
    echo "❌ ERROR: .env not found in the root folder!"
    exit 1
fi

source ../.env

PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
REGION="us-central1"
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
IMAGE_URL="gcr.io/${PROJECT_ID}/nblm-auth-ping"

echo "📦 1. Building Docker image..."
# Rename temporarily so gcloud builds can find it natively
cp Dockerfile.auth Dockerfile
# By building from inside experiments/, we bypass the root .gitignore exclusion!
gcloud builds submit --tag ${IMAGE_URL} .
rm Dockerfile

echo "☁️ 2. Creating Cloud Run Job..."
gcloud run jobs delete nblm-auth-ping --region $REGION --quiet 2>/dev/null || true

gcloud run jobs create nblm-auth-ping \
    --image ${IMAGE_URL} \
    --region $REGION \
    --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}"

echo "⏱️ 3. Creating Cloud Scheduler Trigger (1 PM Every Day)..."
gcloud scheduler jobs delete nblm-auth-ping-cron --location $REGION --quiet 2>/dev/null || true

gcloud scheduler jobs create http nblm-auth-ping-cron \
    --location $REGION \
    --schedule="0 13 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/nblm-auth-ping:run" \
    --http-method POST \
    --oauth-service-account-email "${SERVICE_ACCOUNT}"

echo "✅ Deployment Complete!"
echo "To test it immediately, run: gcloud run jobs execute nblm-auth-ping --region us-central1"
