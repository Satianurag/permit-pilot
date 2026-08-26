#!/usr/bin/env bash
# Cloud Run deploy: combined UI + API, Firestore auth, Cloud DLP.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
IMAGE="us-central1-docker.pkg.dev/${PROJECT}/permit-pilot/app:latest"
SERVICE="permit-pilot"
SECRETS_FILE="${ROOT}/.cloud-deploy.env"

cd "$ROOT"
gcloud config set project "$PROJECT" >/dev/null

if [ -f "$SECRETS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
fi

AUTH_SECRET_KEY="${AUTH_SECRET_KEY:-$(openssl rand -hex 32)}"
CLERK_BOOTSTRAP_PASSWORD="${CLERK_BOOTSTRAP_PASSWORD:-$(openssl rand -base64 18 | tr -d '=+/')}"
CLERK_BOOTSTRAP_USERNAME="${CLERK_BOOTSTRAP_USERNAME:-maria}"
CLERK_BOOTSTRAP_FULL_NAME="${CLERK_BOOTSTRAP_FULL_NAME:-Maria Santos}"
CLERK_BOOTSTRAP_ROLE="${CLERK_BOOTSTRAP_ROLE:-clerk}"

cat >"$SECRETS_FILE" <<EOF
AUTH_SECRET_KEY=${AUTH_SECRET_KEY}
CLERK_BOOTSTRAP_USERNAME=${CLERK_BOOTSTRAP_USERNAME}
CLERK_BOOTSTRAP_PASSWORD=${CLERK_BOOTSTRAP_PASSWORD}
CLERK_BOOTSTRAP_FULL_NAME="${CLERK_BOOTSTRAP_FULL_NAME}"
CLERK_BOOTSTRAP_ROLE=${CLERK_BOOTSTRAP_ROLE}
EOF
chmod 600 "$SECRETS_FILE"

gcloud services enable dlp.googleapis.com cloudtrace.googleapis.com workflows.googleapis.com --project="$PROJECT" 2>/dev/null || true

echo "Building combined image..."
gcloud builds submit --config=cloudbuild.combined.yaml --region="$REGION" .

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)' 2>/dev/null || true)"
if [ -z "$URL" ]; then
  URL="https://${SERVICE}-538666547847.${REGION}.run.app"
fi

echo "Deploying $SERVICE to Cloud Run..."
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
  --timeout 120 \
  --no-cpu-boost \
  --set-env-vars "^@^GOOGLE_CLOUD_PROJECT=${PROJECT}@SEED_ON_STARTUP=false@GOOGLE_GENAI_USE_VERTEXAI=true@GOOGLE_CLOUD_LOCATION=${REGION}@VERTEX_MODEL=gemini-2.5-flash@AGENT_TRUSTED_FINGERPRINTS=d4d19ec3e0bf2828,4963ebd3309933c5,965d7f3302f5b26c,310923e4cdddb79a@GCP_WORKFLOW_NAME=permit-pilot-distribution@AUTH_SECRET_KEY=${AUTH_SECRET_KEY}@CLERK_BOOTSTRAP_USERNAME=${CLERK_BOOTSTRAP_USERNAME}@CLERK_BOOTSTRAP_FULL_NAME=${CLERK_BOOTSTRAP_FULL_NAME}@CLERK_BOOTSTRAP_PASSWORD=${CLERK_BOOTSTRAP_PASSWORD}@CLERK_BOOTSTRAP_ROLE=${CLERK_BOOTSTRAP_ROLE}"

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
gcloud run services update "$SERVICE" \
  --region="$REGION" \
  --update-env-vars "PERMIT_PILOT_URL=${URL}@CORS_ORIGINS=${URL}" >/dev/null || true

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
echo "Cloud Run URL: $URL"

echo "Seeding Cloud Firestore reference cases..."
chmod +x "$ROOT/scripts/seed-cloud.sh"
"$ROOT/scripts/seed-cloud.sh"

echo ""
echo "Live: $URL"
echo "Clerk sign-in: username=${CLERK_BOOTSTRAP_USERNAME}"
echo "Credentials saved to ${SECRETS_FILE} (chmod 600)"
echo "Run audit: source ${SECRETS_FILE} && PERMIT_PILOT_URL=${URL} ./scripts/audit.sh"
