#!/usr/bin/env bash
set -euo pipefail
# Provisions Cloud Tasks, Model Armor, Agent Registry endpoints, Agent Gateway, and Eventarc.
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
ARMOR_LOC="${MODEL_ARMOR_LOCATION:-us-central1}"
NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
API_SA="permit-pilot-api@${PROJECT}.iam.gserviceaccount.com"

gcloud tasks queues describe permit-pilot-distribution --location="$REGION" --project="$PROJECT" >/dev/null 2>&1 \
  || gcloud tasks queues create permit-pilot-distribution --location="$REGION" --project="$PROJECT"

# Model Armor template
if ! gcloud model-armor templates describe permit-pilot-armor --location="$ARMOR_LOC" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud model-armor templates create permit-pilot-armor \
    --location="$ARMOR_LOC" \
    --project="$PROJECT" \
    --pi-and-jailbreak-filter-settings-enforcement=enabled \
    --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above \
    --malicious-uri-filter-settings-enforcement=enabled \
    --rai-settings-filters=filterType=HATE_SPEECH,confidenceLevel=medium-and-above \
    --rai-settings-filters=filterType=DANGEROUS,confidenceLevel=medium-and-above \
    --template-metadata-log-operations \
    --template-metadata-log-sanitize-operations
fi

REGISTRY="//agentregistry.googleapis.com/projects/${PROJECT}/locations/${REGION}"

register_service() {
  local id="$1"
  shift
  if gcloud agent-registry services describe "$id" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
    echo "Agent Registry service exists: $id"
    return 0
  fi
  gcloud agent-registry services create "$id" --location="$REGION" --project="$PROJECT" "$@"
}

register_service nyc-open-data \
  --display-name="NYC Open Data Socrata" \
  --description="Public NYC Open Data (Socrata) REST host for PLUTO, DOB, FDNY, HPD, DEP ECB, and LPC." \
  --endpoint-spec-type=no-spec \
  --interfaces="url=https://data.cityofnewyork.us,protocolBinding=http-json"

register_service agent-registry-api \
  --display-name="Agent Registry API" \
  --description="Google Agent Registry API host required for catalog lookups." \
  --endpoint-spec-type=no-spec \
  --interfaces="url=https://agentregistry.googleapis.com,protocolBinding=http-json"

if [ -z "${MCP_TOOLS_URL:-}" ]; then
  MCP_TOOLS_URL="$(gcloud run services describe permit-pilot-mcp --region="$REGION" --project="$PROJECT" --format='value(status.url)' 2>/dev/null || true)"
fi
if [ -n "${MCP_TOOLS_URL:-}" ]; then
  MCP_MCP_URL="${MCP_TOOLS_URL%/}"
  case "$MCP_MCP_URL" in
    */mcp) ;;
    *) MCP_MCP_URL="${MCP_MCP_URL}/mcp" ;;
  esac
  if ! gcloud agent-registry services describe permit-tools --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
    TOKEN="$(gcloud auth print-access-token)"
    python3 - "$PROJECT" "$REGION" "$MCP_MCP_URL" "$TOKEN" <<'PY'
import json, sys, urllib.request
project, region, url, token = sys.argv[1:]
tools = [
    {"name": "lookup_pluto", "description": "Fetch DCP PLUTO zoning facts for a NYC BBL.", "inputSchema": {"type": "object", "properties": {"bbl": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bbl"]}},
    {"name": "lookup_dob_permits", "description": "Fetch DOB NOW permits for a BBL/BIN.", "inputSchema": {"type": "object", "properties": {"bbl": {"type": "string"}, "bin": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bbl"]}},
    {"name": "lookup_dob_violations", "description": "Fetch active DOB violations for a BIN.", "inputSchema": {"type": "object", "properties": {"bin": {"type": "string"}, "bbl": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bin"]}},
    {"name": "lookup_fdny_violations", "description": "Fetch FDNY violation records for a BIN.", "inputSchema": {"type": "object", "properties": {"bin": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bin"]}},
    {"name": "lookup_hpd_violations", "description": "Fetch HPD violation records for a BIN.", "inputSchema": {"type": "object", "properties": {"bin": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bin"]}},
    {"name": "lookup_dep_ecb", "description": "Fetch DEP ECB violation records for a parcel.", "inputSchema": {"type": "object", "properties": {"bbl": {"type": "string"}, "bin": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bbl"]}},
    {"name": "lookup_landmarks", "description": "Fetch LPC landmark records for a BBL.", "inputSchema": {"type": "object", "properties": {"bbl": {"type": "string"}, "work_type": {"type": "string"}, "case_id": {"type": "string"}}, "required": ["bbl"]}},
    {"name": "validate_citations", "description": "Deterministic cite-or-reject critic.", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]}},
    {"name": "persist_review", "description": "Persist a department review to Firestore.", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}, "department": {"type": "string"}, "status": {"type": "string"}, "summary": {"type": "string"}}, "required": ["case_id", "department", "status", "summary"]}},
]
body = json.dumps({
    "displayName": "Permit Pilot NYC tools",
    "description": "Governed NYC Open Data MCP server for the Permit Pilot fleet.",
    "interfaces": [{"url": url, "protocolBinding": "JSONRPC"}],
    "mcpServerSpec": {"type": "TOOL_SPEC", "content": {"tools": tools}},
}).encode()
req = urllib.request.Request(
    f"https://agentregistry.googleapis.com/v1/projects/{project}/locations/{region}/services?serviceId=permit-tools",
    data=body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST",
)
print(urllib.request.urlopen(req).read().decode()[:300])
PY
  else
    echo "Agent Registry service exists: permit-tools"
  fi
fi

mkdir -p /tmp/permit-pilot-gateway
python3 - "$PROJECT" "$REGION" <<'PY'
from pathlib import Path
import sys
project, region = sys.argv[1], sys.argv[2].rstrip("/")
Path("/tmp/permit-pilot-gateway/egress.yaml").write_text(
    "name: permit-pilot-egress\n"
    "description: Permit Pilot Agent-to-Anywhere egress gateway for NYC MCP tools.\n"
    "protocols:\n"
    "  - MCP\n"
    "googleManaged:\n"
    "  governedAccessPath: AGENT_TO_ANYWHERE\n"
    "registries:\n"
    f"  - //agentregistry.googleapis.com/projects/{project}/locations/{region}\n"
)
PY

gcloud network-services agent-gateways import permit-pilot-egress \
  --source=/tmp/permit-pilot-gateway/egress.yaml \
  --location="$REGION" \
  --project="$PROJECT"

cat >/tmp/permit-pilot-gateway/iap-ext.yaml <<EOF
name: permit-pilot-iap
service: iap.googleapis.com
failOpen: false
timeout: 2s
metadata:
  iamEnforcementMode: "DRY_RUN"
  iapPolicyVersion: "V1"
EOF

gcloud beta service-extensions authz-extensions import permit-pilot-iap \
  --source=/tmp/permit-pilot-gateway/iap-ext.yaml \
  --location="$REGION" \
  --project="$PROJECT" >/dev/null 2>&1 || true

cat >/tmp/permit-pilot-gateway/iap-policy.yaml <<EOF
name: permit-pilot-iap-policy
target:
  resources:
    - "projects/${PROJECT}/locations/${REGION}/agentGateways/permit-pilot-egress"
policyProfile: REQUEST_AUTHZ
action: CUSTOM
customProvider:
  authzExtension:
    resources:
      - "projects/${PROJECT}/locations/${REGION}/authzExtensions/permit-pilot-iap"
EOF

gcloud network-security authz-policies import permit-pilot-iap-policy \
  --source=/tmp/permit-pilot-gateway/iap-policy.yaml \
  --location="$REGION" \
  --project="$PROJECT" >/dev/null 2>&1 || true

# Eventarc: Firestore claim writes resume distribution via Cloud Tasks
EVENTARC_SA="permit-pilot-api@${PROJECT}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${EVENTARC_SA}" \
  --role="roles/eventarc.eventReceiver" \
  --condition=None \
  --quiet >/dev/null

gcloud run services add-iam-policy-binding permit-pilot \
  --region="$REGION" \
  --project="$PROJECT" \
  --member="serviceAccount:${EVENTARC_SA}" \
  --role="roles/run.invoker" \
  --quiet >/dev/null

gcloud eventarc triggers describe permit-pilot-claim-resume --location="$REGION" --project="$PROJECT" >/dev/null 2>&1 || \
  gcloud eventarc triggers create permit-pilot-claim-resume \
    --location="$REGION" \
    --destination-run-service=permit-pilot \
    --destination-run-region="$REGION" \
    --destination-run-path="/api/internal/eventarc/claims" \
    --event-filters="type=google.cloud.firestore.document.v1.updated" \
    --event-filters="database=(default)" \
    --event-filters-path-pattern="document=cases/{case_id}/claims/{claim_id}" \
    --event-data-content-type=application/protobuf \
    --service-account="$EVENTARC_SA" \
    --project="$PROJECT"

# Pub/Sub push OIDC audience must be the Cloud Run origin so the token is
# forwarded into the container (path audiences are consumed by Cloud Run IAM).
RUN_URL="$(gcloud run services describe permit-pilot --region="$REGION" --project="$PROJECT" --format='value(status.url)' 2>/dev/null || true)"
SUB="$(gcloud eventarc triggers describe permit-pilot-claim-resume --location="$REGION" --project="$PROJECT" --format='value(transport.pubsub.subscription)' 2>/dev/null || true)"
if [ -n "$RUN_URL" ] && [ -n "$SUB" ]; then
  SUB_ID="${SUB##*/}"
  PUSH_EP="${RUN_URL%/}/api/internal/eventarc/claims?__GCP_CloudEventsMode=CE_PUBSUB_BINDING"
  gcloud pubsub subscriptions update "$SUB_ID" \
    --project="$PROJECT" \
    --push-endpoint="$PUSH_EP" \
    --push-auth-service-account="$EVENTARC_SA" \
    --push-auth-token-audience="$RUN_URL" \
    --quiet
fi

echo "Platform resources provisioned in $PROJECT / $REGION"
echo "Registry: $REGISTRY"
echo "Model Armor template: permit-pilot-armor"
echo "Gateway: permit-pilot-egress"
echo "Eventarc: permit-pilot-claim-resume"
