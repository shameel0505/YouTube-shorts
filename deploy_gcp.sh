#!/bin/bash
set -e

PROJECT_ID="your-gcp-project-id"    # USER MUST EDIT THIS
REGION="us-central1"
JOB_NAME="youtube-shorts-bot"
IMAGE="gcr.io/${PROJECT_ID}/${JOB_NAME}"
BUCKET="${PROJECT_ID}-shorts-bot"
SERVICE_ACCOUNT="${JOB_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULE_UTC="0 9 * * *"   # 09:00 UTC = 13:00 Dubai time

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Deploying YouTube Shorts Bot"
echo "   Project: $PROJECT_ID | Region: $REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Enable APIs
gcloud services enable \
  run.googleapis.com cloudscheduler.googleapis.com \
  storage.googleapis.com texttospeech.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com \
  --project=$PROJECT_ID

# 2. Create service account
gcloud iam service-accounts create ${JOB_NAME}-sa \
  --display-name="YouTube Shorts Bot SA" --project=$PROJECT_ID 2>/dev/null || true

for role in "roles/storage.objectAdmin" "roles/cloudtexttospeech.user" "roles/run.invoker"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" --role="$role" --quiet 2>/dev/null || true
done

# 3. Create GCS bucket
gcloud storage buckets create gs://${BUCKET} --location=$REGION --project=$PROJECT_ID 2>/dev/null \
  || echo "   (bucket already exists)"

# 4. Store secrets
store_secret() {
  local name=$1 file=$2
  [ -f "$file" ] || { echo "   ⚠️  Skipping $name (file not found: $file)"; return; }
  gcloud secrets create $name --data-file="$file" --project=$PROJECT_ID 2>/dev/null \
    || gcloud secrets versions add $name --data-file="$file" --project=$PROJECT_ID
  echo "   ✅ Secret: $name"
}
store_secret "youtube-token"         "./token.json"
store_secret "youtube-client-secret" "./client_secret.json"
store_secret "env-config"            "./.env"

# 5. Build Docker image
echo "🐳 Building image..."
gcloud builds submit --tag $IMAGE --project=$PROJECT_ID .

# 6. Deploy Cloud Run Job
echo "☁️  Deploying Cloud Run Job..."
gcloud run jobs create $JOB_NAME \
  --image=$IMAGE --region=$REGION --service-account=$SERVICE_ACCOUNT \
  --memory=2Gi --cpu=2 --task-timeout=1800 --max-retries=1 \
  --project=$PROJECT_ID \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCS_BUCKET=${BUCKET}" \
  2>/dev/null \
  || gcloud run jobs update $JOB_NAME \
    --image=$IMAGE --region=$REGION --memory=2Gi --cpu=2 \
    --project=$PROJECT_ID

# 7. Cloud Scheduler
echo "⏰ Setting up daily scheduler..."
JOB_URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"
gcloud scheduler jobs create http ${JOB_NAME}-trigger \
  --location=$REGION --schedule="$SCHEDULE_UTC" \
  --uri="$JOB_URL" --http-method=POST \
  --oauth-service-account-email=$SERVICE_ACCOUNT \
  --project=$PROJECT_ID 2>/dev/null \
  || gcloud scheduler jobs update http ${JOB_NAME}-trigger \
    --schedule="$SCHEDULE_UTC" --location=$REGION --project=$PROJECT_ID

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Done! Bot posts daily at 09:00 UTC (13:00 Dubai)"
echo ""
echo "Manual trigger: gcloud run jobs execute $JOB_NAME --region=$REGION"
echo "View logs:      gcloud run jobs executions list --job=$JOB_NAME --region=$REGION"
echo "Update code:    gcloud builds submit --tag $IMAGE && gcloud run jobs update $JOB_NAME --image=$IMAGE --region=$REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
