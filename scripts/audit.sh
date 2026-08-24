#!/usr/bin/env bash
# Production verification against Cloud Run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${PERMIT_PILOT_URL:-https://permit-pilot-538666547847.us-central1.run.app}"

if [ -f "${ROOT}/.cloud-deploy.env" ]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.cloud-deploy.env"
fi

USER="${CLERK_BOOTSTRAP_USERNAME:-maria}"
PASS="${CLERK_BOOTSTRAP_PASSWORD:?Set CLERK_BOOTSTRAP_PASSWORD or run ./scripts/deploy.sh first}"

echo "=== 0. Clerk auth ==="
TOKEN=$(curl -fsS -X POST "$BASE/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${USER}&password=${PASS}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH=(-H "Authorization: Bearer $TOKEN")

echo "=== 1. Health ==="
curl -fsS "$BASE/api/health" | grep -q ok

echo "=== 2. Unauthenticated API blocked ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/tasks")
test "$CODE" = "401"

echo "=== 3. Tasks (Firestore, open only) ==="
TASKS=$(curl -fsS "${AUTH[@]}" "$BASE/api/tasks")
echo "$TASKS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=1, 'no open tasks'"

echo "=== 4. Case bundle + distribution (live Socrata-backed) ==="
CASE_ID=$(echo "$TASKS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['case_id'])")
curl -fsS "${AUTH[@]}" "$BASE/api/cases/$CASE_ID/bundle" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['distribution'])>=5; util=[r for r in d['distribution'] if r['department']=='utilities'][0]; assert 'skr7-cxt3' in str(util['evidence']), 'utilities must use DEP ECB'"

echo "=== 5. Clerk briefing ==="
curl -fsS "${AUTH[@]}" -X POST "$BASE/api/cases/$CASE_ID/orchestrate" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('summary')"

echo "=== 6. Trace + observability ==="
curl -fsS "${AUTH[@]}" "$BASE/api/cases/$CASE_ID/trace" >/dev/null
curl -fsS "${AUTH[@]}" "$BASE/api/config/observability?case_id=$CASE_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('cloud_trace_url')"

echo "=== 7. Permit search ==="
curl -fsS "${AUTH[@]}" "$BASE/api/cases?q=BIN" >/dev/null

echo "=== 8. SPA login route ==="
curl -fsS -o /dev/null -w "%{http_code}\n" "$BASE/login" | grep -q 200

echo "ALL CHECKS PASSED — $BASE"
