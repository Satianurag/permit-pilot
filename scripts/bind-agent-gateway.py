#!/usr/bin/env python3
"""Rebind every Agent Runtime engine to the Agent Gateway (AGENT_TO_ANYWHERE)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/permit_pilot_core"))

from google.auth import default  # noqa: E402
from google.auth.transport.requests import Request  # noqa: E402
import httpx  # noqa: E402

from permit_pilot_core.platform.runtime import engine_resource  # noqa: E402
from permit_pilot_core.settings import get_settings  # noqa: E402


def _token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def main() -> None:
    settings = get_settings()
    engines_path = ROOT / ".agent-engines.json"
    mapping = json.loads(engines_path.read_text())
    gateway = (
        f"projects/{settings.project_id}/locations/{settings.region}/"
        f"agentGateways/{settings.agent_gateway_name}"
    )
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }
    body = {
        "spec": {
            "deploymentSpec": {
                "agentGatewayConfig": {
                    "agentToAnywhereConfig": {"agentGateway": gateway}
                }
            }
        }
    }
    failures: list[str] = []
    for name, engine_id in mapping.items():
        resource = engine_resource(str(engine_id))
        url = (
            f"https://{settings.region}-aiplatform.googleapis.com/v1beta1/{resource}"
            "?updateMask=spec.deploymentSpec.agentGatewayConfig"
        )
        print(f"Binding {name} ({engine_id}) -> {gateway}", flush=True)
        response = httpx.patch(url, headers=headers, json=body, timeout=120.0)
        if response.status_code >= 400:
            alt = {
                "agentGatewayConfig": {
                    "agentToAnywhereConfig": {"agentGateway": gateway}
                }
            }
            url2 = (
                f"https://{settings.region}-aiplatform.googleapis.com/v1beta1/{resource}"
                "?updateMask=agentGatewayConfig"
            )
            response = httpx.patch(url2, headers=headers, json=alt, timeout=120.0)
        if response.status_code >= 400:
            failures.append(f"{name}: {response.status_code} {response.text[:500]}")
            print(f"  FAILED {response.status_code}: {response.text[:300]}", flush=True)
            continue
        print(f"  ok {response.status_code}", flush=True)
    if failures:
        print("FAILURES:")
        for item in failures:
            print(f" - {item}")
        raise SystemExit(1)
    print("gateway bind complete")


if __name__ == "__main__":
    main()
