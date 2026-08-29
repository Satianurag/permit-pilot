#!/usr/bin/env bash
# Configure Google Sign-In on Cloud Run using gcloud + curl only.
#
# Google does NOT expose GIS OAuth 2.0 Web client creation (the
# *.apps.googleusercontent.com type with authorized JS origins) via gcloud.
# Create that client once in Google Auth Platform (Console), then run:
#
#   export GOOGLE_SIGNIN_CLIENT_ID=123456789-abc.apps.googleusercontent.com
#   ./scripts/configure-google-signin.sh
#
# Or add GOOGLE_SIGNIN_CLIENT_ID to .cloud-deploy.env and run without exports.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.cloud-deploy.env"
PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE="${GOOGLE_SIGNIN_SERVICE:-permit-pilot}"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1091
  source "$ENV_FILE"
fi

CLIENT_ID="${GOOGLE_SIGNIN_CLIENT_ID:-}"
if [ -z "$CLIENT_ID" ]; then
  echo "GOOGLE_SIGNIN_CLIENT_ID is required." >&2
  echo >&2
  echo "One-time Console step (no gcloud command exists for GIS web clients):" >&2
  URL="$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(status.url)' 2>/dev/null || true)"
  echo "  1. Open Google Auth Platform → Clients for project ${PROJECT}" >&2
  echo "  2. Create a Web application client named 'Permit Pilot Web'" >&2
  echo "  3. Add authorized JavaScript origins:" >&2
  [ -n "$URL" ] && echo "       ${URL}" >&2
  echo "       https://permit-pilot-pbrfw2zkaq-uc.a.run.app" >&2
  echo "       https://permit-pilot-538666547847.us-central1.run.app" >&2
  echo "  4. Export the client id, then re-run this script." >&2
  exit 1
fi

if [[ "$CLIENT_ID" != *".apps.googleusercontent.com" ]]; then
  echo "GOOGLE_SIGNIN_CLIENT_ID must be a GIS web client (*.apps.googleusercontent.com)." >&2
  echo "gcloud iam oauth-clients create produces Workforce IDs and will not work here." >&2
  exit 1
fi

gcloud config set project "$PROJECT" >/dev/null

echo "Updating Cloud Run service ${SERVICE}…"
gcloud run services update "$SERVICE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --update-env-vars "GOOGLE_SIGNIN_CLIENT_ID=${CLIENT_ID}" >/dev/null

if [ -f "$ENV_FILE" ] && ! grep -q '^GOOGLE_SIGNIN_CLIENT_ID=' "$ENV_FILE"; then
  echo "GOOGLE_SIGNIN_CLIENT_ID=${CLIENT_ID}" >> "$ENV_FILE"
  echo "Appended GOOGLE_SIGNIN_CLIENT_ID to .cloud-deploy.env"
elif [ -f "$ENV_FILE" ]; then
  echo "Note: .cloud-deploy.env already defines GOOGLE_SIGNIN_CLIENT_ID; Cloud Run was updated."
fi

BASE="$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(status.url)')"
LIVE_ID="$(curl -fsS "${BASE}/api/auth/google-client" | python3 -c "import sys,json; print(json.load(sys.stdin).get('client_id',''))")"
if [ "$LIVE_ID" != "$CLIENT_ID" ]; then
  echo "Verification failed: live client_id='${LIVE_ID}' expected '${CLIENT_ID}'" >&2
  exit 1
fi

echo "OK: ${BASE}/api/auth/google-client returns the configured client id."
echo "Open ${BASE}/login and confirm the Google button renders."
