#!/usr/bin/env bash
# Cost-conscious Cloud Run deploy: one public service, API internal to container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
IMAGE="us-central1-docker.pkg.dev/${PROJECT}/permit-pilot/app:latest"
SERVICE="permit-pilot"

cd "$ROOT"
gcloud config set project "$PROJECT" >/dev/null

gcloud services enable dlp.googleapis.com cloudtrace.googleapis.com workflows.googleapis.com --project="$PROJECT" 2>/dev/null || true

echo "Building combined image..."
gcloud builds submit --config=cloudbuild.combined.yaml --region="$REGION" .

echo "Deploying $SERVICE (scale-to-zero, max 1 instance)..."
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --cpu-throttling \
  --max-instances 1 \
  --min-instances 0 \
  --concurrency 80 \
  --timeout 60 \
  --no-cpu-boost \
  --set-env-vars "^@^GOOGLE_CLOUD_PROJECT=${PROJECT}@SEED_ON_STARTUP=false@GOOGLE_GENAI_USE_VERTEXAI=true@GOOGLE_CLOUD_LOCATION=us-central1@VERTEX_MODEL=gemini-2.5-flash@AGENT_TRUSTED_FINGERPRINTS=d4d19ec3e0bf2828,4963ebd3309933c5,965d7f3302f5b26c,310923e4cdddb79a@GCP_WORKFLOW_NAME=permit-pilot-distribution@PERMIT_PILOT_URL=https://permit-pilot-538666547847.us-central1.run.app"

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
echo ""
echo "Live: $URL"
echo "Single service: UI + /api on same origin (no separate public API host)."
