#!/usr/bin/env bash
# ADK orchestrator on Cloud Run — scale to zero, no public invoker (optional demo URL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
IMAGE="us-central1-docker.pkg.dev/${PROJECT}/permit-pilot/orchestrator:latest"
SERVICE="permit-pilot-orchestrator"

cd "$ROOT"
gcloud services enable aiplatform.googleapis.com --project="$PROJECT" 2>/dev/null || true

gcloud builds submit --config=cloudbuild.orchestrator.yaml --region="$REGION" --project="$PROJECT" .

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --cpu-throttling \
  --max-instances 1 \
  --min-instances 0 \
  --no-cpu-boost \
  --timeout 120 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true"

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT" --format='value(status.url)')"
echo "ADK orchestrator: $URL"
