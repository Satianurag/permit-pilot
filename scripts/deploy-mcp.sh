#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/permit-pilot/mcp:latest"
SERVICE="permit-pilot-mcp"
MCP_SA="permit-pilot-mcp@${PROJECT}.iam.gserviceaccount.com"
NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"

cd "$ROOT"
gcloud builds submit --config=cloudbuild.mcp.yaml --region="$REGION" --substitutions=_IMAGE="$IMAGE" .

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --service-account "$MCP_SA" \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 4 \
  --timeout 120 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_PROJECT_NUMBER=${NUM},GOOGLE_CLOUD_LOCATION=${REGION}"

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
# Agent Runtime needs to invoke MCP
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" \
  --member="serviceAccount:service-${NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/run.invoker" --quiet >/dev/null || true
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" \
  --member="serviceAccount:permit-pilot-api@${PROJECT}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" --quiet >/dev/null

echo "MCP_TOOLS_URL=$URL"
