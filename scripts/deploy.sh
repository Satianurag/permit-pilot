#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
VERTEX_MODEL="${VERTEX_MODEL:-gemini-3.5-flash}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/permit-pilot/app:latest"
SERVICE="permit-pilot"
API_SA="permit-pilot-api@${PROJECT}.iam.gserviceaccount.com"
TASKS_SA="permit-pilot-tasks@${PROJECT}.iam.gserviceaccount.com"
NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"

cd "$ROOT"
gcloud config set project "$PROJECT" >/dev/null
gcloud artifacts repositories describe permit-pilot --location="$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create permit-pilot --repository-format=docker --location="$REGION"

gcloud builds submit --config=cloudbuild.combined.yaml --region="$REGION" --substitutions=_IMAGE="$IMAGE" .

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)' 2>/dev/null || true)"

if [ -z "${AGENT_ENGINE_IDS:-}" ] && [ -f "$ROOT/.agent-engines.json" ]; then
  AGENT_ENGINE_IDS="$(python3 -c 'import json,pathlib; m=json.loads(pathlib.Path("'"$ROOT"'/.agent-engines.json").read_text()); print(",".join(f"{k}={v}" for k,v in m.items()))')"
fi
if [ -z "${ORCHESTRATOR_ENGINE_ID:-}" ] && [ -f "$ROOT/.agent-engines.json" ]; then
  ORCHESTRATOR_ENGINE_ID="$(python3 -c 'import json,pathlib; print(json.loads(pathlib.Path("'"$ROOT"'/.agent-engines.json").read_text()).get("permit_orchestrator",""))')"
fi

ENV_FILE="$(mktemp)"
{
  echo "GOOGLE_CLOUD_PROJECT: '${PROJECT}'"
  echo "GOOGLE_CLOUD_PROJECT_NUMBER: '${NUM}'"
  echo "GOOGLE_CLOUD_LOCATION: '${REGION}'"
  echo "VERTEX_LOCATION: '${VERTEX_LOCATION}'"
  echo "VERTEX_MODEL: '${VERTEX_MODEL}'"
  echo "GOOGLE_GENAI_USE_VERTEXAI: 'true'"
  echo "SEED_ON_STARTUP: 'false'"
  echo "CLOUD_TASKS_QUEUE: 'permit-pilot-distribution'"
  echo "CLOUD_TASKS_SERVICE_ACCOUNT: '${TASKS_SA}'"
  echo "AGENT_STAGING_BUCKET: 'gs://permit-pilot-agent-staging-${NUM}'"
  echo "MODEL_ARMOR_TEMPLATE: 'permit-pilot-armor'"
  echo "AGENT_GATEWAY_NAME: 'permit-pilot-egress'"
  echo "CLERK_BOOTSTRAP_USERNAME: '${CLERK_BOOTSTRAP_USERNAME:-maria}'"
  echo "CLERK_BOOTSTRAP_FULL_NAME: '${CLERK_BOOTSTRAP_FULL_NAME:-Maria Santos}'"
  echo "CLERK_BOOTSTRAP_ROLE: 'clerk'"
  if [ -n "${ORCHESTRATOR_ENGINE_ID:-}" ]; then
    echo "ORCHESTRATOR_ENGINE_ID: '${ORCHESTRATOR_ENGINE_ID}'"
  fi
  if [ -n "${AGENT_ENGINE_IDS:-}" ]; then
    echo "AGENT_ENGINE_IDS: '${AGENT_ENGINE_IDS}'"
  fi
  if [ -n "${MCP_TOOLS_URL:-}" ]; then
    echo "MCP_TOOLS_URL: '${MCP_TOOLS_URL}'"
  fi
} > "$ENV_FILE"

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "$API_SA" \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1 \
  --timeout 300 \
  --env-vars-file "$ENV_FILE" \
  --set-secrets "AUTH_SECRET_KEY=permit-pilot-auth-secret:latest,CLERK_BOOTSTRAP_PASSWORD=permit-pilot-clerk-password:latest"
rm -f "$ENV_FILE"

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
gcloud run services update "$SERVICE" \
  --region="$REGION" \
  --update-env-vars "PERMIT_PILOT_URL=${URL},CORS_ORIGINS=${URL}" >/dev/null

gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" \
  --member="serviceAccount:${TASKS_SA}" \
  --role="roles/run.invoker" --quiet >/dev/null

echo "Cloud Run URL: $URL"
echo "Clerk username: ${CLERK_BOOTSTRAP_USERNAME:-maria}"
echo "Password is in Secret Manager: permit-pilot-clerk-password"
