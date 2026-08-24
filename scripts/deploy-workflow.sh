#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
WORKFLOW="permit-pilot-distribution"
SERVICE_URL="${PERMIT_PILOT_URL:-https://permit-pilot-538666547847.us-central1.run.app}"

gcloud services enable workflows.googleapis.com workflowexecutions.googleapis.com --project="$PROJECT"

gcloud workflows deploy "$WORKFLOW" \
  --source="$ROOT/infra/workflows/distribution.yaml" \
  --location="$REGION" \
  --project="$PROJECT"

# Workflow SA needs to invoke Cloud Run API with OIDC
PROJECT_NUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
WF_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
gcloud run services add-iam-policy-binding permit-pilot \
  --region="$REGION" \
  --project="$PROJECT" \
  --member="serviceAccount:${WF_SA}" \
  --role="roles/run.invoker" \
  --quiet

echo "Deployed workflow: $WORKFLOW"
echo "Set on Cloud Run: GCP_WORKFLOW_NAME=$WORKFLOW PERMIT_PILOT_URL=$SERVICE_URL"
