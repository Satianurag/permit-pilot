#!/usr/bin/env bash
set -euo pipefail
# Grant fleet Agent Identity principals MCP Cloud Run access and ID token mint rights.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE="${MCP_SERVICE_NAME:-permit-pilot-mcp}"
IDENTITIES="${ROOT}/.agent-identities.json"
ENGINES="${ROOT}/.agent-engines.json"
INVOKER_SA="permit-pilot-api@${PROJECT}.iam.gserviceaccount.com"

if [ ! -f "$IDENTITIES" ] && [ ! -f "$ENGINES" ]; then
  echo "Missing .agent-identities.json and .agent-engines.json; deploy fleet first." >&2
  exit 1
fi

NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
python3 - "$ROOT" "$PROJECT" "$REGION" "$SERVICE" "$NUM" "$INVOKER_SA" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
project, region, service, num, invoker_sa = sys.argv[2:7]

def agent_iap_principal(engine_id: str) -> str:
    spiffe = (
        f"agents.global.proj-{num}.system.id.goog/resources/"
        f"aiplatform/projects/{num}/locations/{region}/reasoningEngines/{engine_id}"
    )
    return f"principal://{spiffe}"

ident_path = root / ".agent-identities.json"
engines_path = root / ".agent-engines.json"
identities: dict[str, dict] = {}
if ident_path.exists():
    identities = json.loads(ident_path.read_text()) or {}
engines: dict[str, str] = {}
if engines_path.exists():
    engines = json.loads(engines_path.read_text()) or {}

names = sorted(set(identities) | set(engines))
if not names:
    raise SystemExit("No fleet agents found in identity files")

for name in names:
    row = identities.get(name) or {}
    engine_id = row.get("engine_id") or engines.get(name)
    if not engine_id:
        print(f"SKIP {name}: no engine_id", flush=True)
        continue
    member = row.get("iap_principal") or row.get("runtime_identity")
    if not member:
        member = agent_iap_principal(str(engine_id))
    elif not member.startswith("principal://"):
        member = f"principal://{member}"
    print(f"Binding run.invoker {name} -> {member}", flush=True)
    subprocess.check_call(
        [
            "gcloud",
            "run",
            "services",
            "add-iam-policy-binding",
            service,
            f"--region={region}",
            f"--member={member}",
            "--role=roles/run.invoker",
            "--quiet",
        ]
    )
    print(f"Binding token creator {name} -> {invoker_sa}", flush=True)
    subprocess.check_call(
        [
            "gcloud",
            "iam",
            "service-accounts",
            "add-iam-policy-binding",
            invoker_sa,
            f"--member={member}",
            "--role=roles/iam.serviceAccountTokenCreator",
            "--quiet",
        ]
    )
print("MCP run.invoker and serviceAccountTokenCreator bindings applied.")
PY
