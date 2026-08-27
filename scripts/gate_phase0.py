"""Phase 0 gate: prove gemini-3.5-flash and Agent Identity work on Agent Runtime.

Deploys a throwaway ADK agent, queries it, prints the SPIFFE identity, deletes it.
Run once before building the fleet. Not part of the shipped product.
"""

from __future__ import annotations

import os
import sys

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ.get("AGENT_RUNTIME_LOCATION", "us-central1")
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "global")
MODEL = os.environ.get("VERTEX_MODEL", "gemini-3.5-flash")
STAGING = f"gs://{PROJECT}-agent-staging"


def main() -> int:
    from agentplatform import Client
    from agentplatform._genai.types.common import IdentityType
    from agentplatform.agent_engines import AdkApp
    from google.adk.agents import Agent
    from google.adk.apps import App

    client = Client(project=PROJECT, location=REGION)

    probe = Agent(
        name="phase0_probe",
        model=MODEL,
        description="Phase 0 gate probe.",
        instruction="Reply with exactly: GATE_OK",
    )
    app = AdkApp(app=App(name="phase0_probe", root_agent=probe), enable_tracing=True)

    print(f"Deploying probe to Agent Runtime ({REGION}) with model {MODEL}...")
    remote = client.agent_engines.create(
        agent=app,
        config={
            "display_name": "phase0-gate-probe",
            "identity_type": IdentityType.AGENT_IDENTITY,
            "staging_bucket": STAGING,
            "requirements": [
                "google-cloud-aiplatform[adk,agent_engines]",
                "google-adk",
            ],
            "env_vars": {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_LOCATION": VERTEX_LOCATION,
            },
            "min_instances": 0,
            "max_instances": 1,
        },
    )

    name = remote.api_resource.name
    engine_id = name.rsplit("/", 1)[-1]
    print(f"\nDeployed: {name}")

    detail = client.agent_engines.get(name=name)
    identity = getattr(detail, "effective_identity", None) or getattr(
        getattr(detail, "api_resource", None), "effective_identity", None
    )
    print(f"engine_id        = {engine_id}")
    print(f"effectiveIdentity= {identity}")

    print("\nQuerying the deployed agent...")
    ok = False
    try:
        chunks = [
            str(event)
            for event in remote.stream_query(user_id="phase0", message="ping")
        ]
        blob = " ".join(chunks)
        print("response snippet:", blob[:800])
        ok = "GATE_OK" in blob
    except Exception as exc:  # noqa: BLE001 - gate must report, not crash
        print(f"QUERY FAILED: {type(exc).__name__}: {exc}")

    print("\nCleaning up probe...")
    try:
        client.agent_engines.delete(name=name, config={"force": True})
        print("deleted.")
    except Exception as exc:  # noqa: BLE001
        print(f"delete failed (remove manually): {exc}")

    print("\n" + ("GATE PASSED" if ok else "GATE FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
