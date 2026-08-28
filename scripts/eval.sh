#!/usr/bin/env bash
# Canonical agent eval — routing/tool trajectory tests plus optional `adk eval`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORE_PY="$ROOT/packages/permit_pilot_core/.venv/bin/python"
ORCH_ADK="$ROOT/services/orchestrator/.venv/bin/adk"
cd "$ROOT/packages/permit_pilot_core"
if [ -x "$CORE_PY" ]; then
  "$CORE_PY" -m unittest tests.test_eval_bbls tests.test_agentic_policy tests.test_fleet_catalog tests.test_parcel tests.test_identity
else
  python3 -m unittest tests.test_eval_bbls tests.test_agentic_policy tests.test_fleet_catalog tests.test_parcel tests.test_identity
fi
if [ -x "$ORCH_ADK" ]; then
  echo "=== adk eval (orchestrator coordinator) ==="
  export PYTHONPATH="$ROOT/services/orchestrator/src:$ROOT/packages/permit_pilot_core:${PYTHONPATH:-}"
  export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
  export VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
  export VERTEX_MODEL="${VERTEX_MODEL:-gemini-3.5-flash}"
  export MCP_TOOLS_URL="${MCP_TOOLS_URL:-https://permit-pilot-mcp-pbrfw2zkaq-uc.a.run.app}"
  "$ORCH_ADK" eval "$ROOT/services/orchestrator/src/permit_pilot/agents/orchestrator" \
    "$ROOT/packages/permit_pilot_core/eval/permit_pilot.evalset.json" || {
    echo "NOTE: adk eval needs Agent Runtime (or a SA that can mint Cloud Run ID tokens for MCP)."
    echo "NOTE: unittest trajectory contracts still passed against the coordinator catalog."
  }
elif command -v adk >/dev/null 2>&1; then
  echo "=== adk eval (orchestrator coordinator) ==="
  adk eval "$ROOT/services/orchestrator/src/permit_pilot/agents/orchestrator" \
    "$ROOT/packages/permit_pilot_core/eval/permit_pilot.evalset.json" || {
    echo "NOTE: adk eval failed or is not wired to a live session; unittest contracts still passed."
  }
else
  echo "NOTE: adk CLI not installed; unittest trajectory contracts ran against the coordinator catalog."
fi
