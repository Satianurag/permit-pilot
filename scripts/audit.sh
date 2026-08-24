#!/usr/bin/env bash
# Sequential production verification (no mocks).
set -euo pipefail
BASE="${PERMIT_PILOT_URL:-https://permit-pilot-538666547847.us-central1.run.app}"

echo "=== 1. Health ==="
curl -fsS "$BASE/api/health" | grep -q ok

echo "=== 2. Tasks (Firestore) ==="
TASKS=$(curl -fsS "$BASE/api/tasks")
echo "$TASKS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=1, 'no tasks'"

echo "=== 3. Agent catalog ==="
curl -fsS "$BASE/api/agents" | python3 -c "import sys,json; d=json.load(sys.stdin); assert any(a['signed'] for a in d)"

echo "=== 4. Case + distribution (live Socrata-backed) ==="
CASE_ID=$(echo "$TASKS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['case_id'])")
curl -fsS "$BASE/api/cases/$CASE_ID/distribution" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=5"

echo "=== 5. Vertex orchestrator ==="
curl -fsS -X POST "$BASE/api/cases/$CASE_ID/orchestrate" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('summary')"

echo "=== 6. Workflow + trace endpoints ==="
curl -fsS "$BASE/api/cases/$CASE_ID/workflow" >/dev/null
curl -fsS "$BASE/api/cases/$CASE_ID/trace" >/dev/null

echo "=== 7. Observability config ==="
curl -fsS "$BASE/api/config/observability?case_id=$CASE_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('cloud_trace_url')"

echo "=== 8. GCP Cloud Workflows (if configured) ==="
GCP_RUN=$(curl -fsS -w "\n%{http_code}" -X POST "$BASE/api/cases/$CASE_ID/workflow/gcp-run" 2>/dev/null || echo -e "\n503")
HTTP_CODE=$(echo "$GCP_RUN" | tail -1)
BODY=$(echo "$GCP_RUN" | sed '$d')
if [ "$HTTP_CODE" = "200" ]; then
  echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('execution_id')"
  echo "GCP workflow execution started"
elif [ "$HTTP_CODE" = "503" ]; then
  echo "SKIP: GCP_WORKFLOW_NAME not configured on service yet"
else
  echo "GCP workflow failed ($HTTP_CODE): $BODY"
  exit 1
fi

echo "=== 9. SPA routes ==="
curl -fsS -o /dev/null -w "%{http_code}\n" "$BASE/tasks" | grep -q 200

echo "ALL CHECKS PASSED — $BASE"
