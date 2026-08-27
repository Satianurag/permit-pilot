#!/usr/bin/env bash
set -euo pipefail
# Grant each fleet agent's Agent Registry RuntimeIdentity roles/iap.egressor
# on only the MCP tools in its catalog. Zoning cannot reach lookup_hpd_violations.
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/packages/permit_pilot_core"
exec python3 - "$ROOT" "$PROJECT" "$REGION" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from permit_pilot_core.platform.fleet import FLEET
from permit_pilot_core.platform.iap_bindings import (
    endpoint_egressor_bindings,
    mcp_egressor_bindings,
)

root = Path(sys.argv[1])
project, region = sys.argv[2], sys.argv[3]


def gcloud(*args: str, json_out: bool = False) -> str:
    cmd = ["gcloud", *args]
    if json_out:
        cmd += ["--format=json"]
    return subprocess.check_output(cmd, text=True)


def gcloud_ok(*args: str) -> str:
    return subprocess.check_output(args, text=True)


def registry_child_id(service_id: str) -> str:
    raw = gcloud_ok(
        "gcloud",
        "agent-registry",
        "services",
        "describe",
        service_id,
        "--location",
        region,
        "--project",
        project,
        "--format=value(registryResource)",
    ).strip()
    return raw.rsplit("/", 1)[-1]


def runtime_principals() -> dict[str, str]:
    agents = json.loads(
        gcloud(
            "agent-registry",
            "agents",
            "list",
            f"--location={region}",
            f"--project={project}",
            json_out=True,
        )
    )
    found: dict[str, str] = {}
    for item in agents:
        display = item.get("displayName") or ""
        principal = (
            (item.get("attributes") or {})
            .get("agentregistry.googleapis.com/system/RuntimeIdentity", {})
            .get("principal")
        )
        if display in {spec.name for spec in FLEET} and principal:
            found[display] = principal
    missing = [spec.name for spec in FLEET if spec.name not in found]
    if missing:
        raise SystemExit(f"Agent Registry RuntimeIdentity missing for: {missing}")
    return found


def get_policy(*, mcp_server: str | None = None, endpoint: str | None = None) -> dict:
    args = [
        "gcloud",
        "beta",
        "iap",
        "web",
        "get-iam-policy",
        "--resource-type=agent-registry",
        f"--region={region}",
        f"--project={project}",
        "--format=json",
    ]
    if mcp_server:
        args.append(f"--mcp-server={mcp_server}")
    if endpoint:
        args.append(f"--endpoint={endpoint}")
    return json.loads(subprocess.check_output(args, text=True))


def set_policy(policy: dict, *, mcp_server: str | None = None, endpoint: str | None = None) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(policy, fh)
        path = fh.name
    args = [
        "gcloud",
        "beta",
        "iap",
        "web",
        "set-iam-policy",
        path,
        "--resource-type=agent-registry",
        f"--region={region}",
        f"--project={project}",
        "--quiet",
    ]
    if mcp_server:
        args.append(f"--mcp-server={mcp_server}")
    if endpoint:
        args.append(f"--endpoint={endpoint}")
    try:
        subprocess.check_call(args)
    finally:
        Path(path).unlink(missing_ok=True)


def extra_unconditional_members(policy: dict) -> list[str]:
    keep: list[str] = []
    for binding in policy.get("bindings") or []:
        if binding.get("role") != "roles/iap.egressor" or binding.get("condition"):
            continue
        for member in binding.get("members") or []:
            if member.startswith("serviceAccount:") and member not in keep:
                keep.append(member)
    return keep


mcp_id = registry_child_id("permit-tools")
endpoint_id = registry_child_id("nyc-open-data")
principals = runtime_principals()
print("mcp-server=", mcp_id)
print("endpoint=", endpoint_id)
for name, principal in principals.items():
    print(f"  {name} {principal}")

current_mcp = get_policy(mcp_server=mcp_id)
mcp_policy = {
    "bindings": mcp_egressor_bindings(
        principals=principals,
        extra_members=extra_unconditional_members(current_mcp),
    ),
    "etag": current_mcp.get("etag", ""),
    "version": 3,
}
print("Applying MCP per-tool IAP egressor bindings...")
set_policy(mcp_policy, mcp_server=mcp_id)

current_ep = get_policy(endpoint=endpoint_id)
ep_policy = {
    "bindings": endpoint_egressor_bindings(principals=principals),
    "etag": current_ep.get("etag", ""),
    "version": 3,
}
print("Applying NYC Open Data endpoint IAP egressor bindings...")
set_policy(ep_policy, endpoint=endpoint_id)

ident_path = root / ".agent-identities.json"
existing = {}
if ident_path.exists():
    try:
        existing = json.loads(ident_path.read_text()) or {}
    except json.JSONDecodeError:
        existing = {}
for spec in FLEET:
    row = existing.get(spec.name) or {}
    principal = principals[spec.name]
    row["iap_principal"] = principal
    row["runtime_identity"] = principal
    existing[spec.name] = row
ident_path.write_text(json.dumps(existing, indent=2) + "\n")

applied = get_policy(mcp_server=mcp_id)
zoning = next(
    item
    for item in applied.get("bindings") or []
    if (item.get("condition") or {}).get("title") == "zoning_agent-tools"
)
expression = zoning["condition"]["expression"]
if "lookup_hpd_violations" in expression:
    raise SystemExit("zoning IAP CEL includes lookup_hpd_violations")
if "lookup_pluto" not in expression:
    raise SystemExit("zoning IAP CEL missing lookup_pluto")
titles = {
    (item.get("condition") or {}).get("title")
    for item in applied.get("bindings") or []
    if item.get("condition")
}
expected = {f"{spec.name}-tools" for spec in FLEET}
missing = expected - titles
if missing:
    raise SystemExit(f"missing IAP conditions: {sorted(missing)}")
print("Least-privilege IAP egressor bindings applied.")
print("Verified: zoning CEL has lookup_pluto and not lookup_hpd_violations.")
PY
