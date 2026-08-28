#!/usr/bin/env python3
"""Deploy ADK fleet agents to Agent Runtime with Agent Identity.

Gateway binding happens in Phase 3 after the Agent Gateway exists.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/permit_pilot_core"))
sys.path.insert(0, str(ROOT / "services/orchestrator/src"))
os.chdir(ROOT)

from permit_pilot_core.platform.fleet import FLEET  # noqa: E402
from permit_pilot_core.settings import get_settings  # noqa: E402

MODULE_BY_AGENT = {
    "permit_orchestrator": "orchestrator",
}


def _stringify_env(values: dict[str, str]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


def _build_wheels(wheel_dir: Path) -> list[Path]:
    wheel_dir.mkdir(parents=True, exist_ok=True)
    for src in (
        ROOT / "packages/permit_pilot_core",
        ROOT / "services/orchestrator",
    ):
        subprocess.check_call(
            ["uv", "build", "--wheel", "--out-dir", str(wheel_dir), str(src)]
        )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) < 2:
        raise SystemExit(f"Expected two local wheels, found {wheels}")
    return wheels


def _existing_by_display_name(client) -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        pager = client.agent_engines.list()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not list existing engines ({exc}); will create.")
        return found
    for item in pager:
        resource = getattr(item, "api_resource", item)
        display = getattr(resource, "display_name", None) or getattr(
            item, "display_name", None
        )
        name = getattr(resource, "name", None) or getattr(item, "name", None)
        if display and name:
            found[display] = name
    return found


def _effective_identity(detail) -> str:
    resource = getattr(detail, "api_resource", detail)
    identity = (
        getattr(detail, "effective_identity", None)
        or getattr(resource, "effective_identity", None)
        or ""
    )
    return str(identity)


def _write_env_keys(mapping: dict[str, str]) -> None:
    env_path = ROOT / ".cloud-deploy.env"
    csv = ",".join(f"{name}={engine_id}" for name, engine_id in mapping.items())
    orchestrator = mapping.get("permit_orchestrator", "")
    updates = {
        "AGENT_ENGINE_IDS": csv,
        "ORCHESTRATOR_ENGINE_ID": orchestrator,
    }
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            existing[key] = value
    existing.update(updates)
    lines = [f"{key}={value}" for key, value in existing.items()]
    env_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    settings = get_settings()
    if not settings.project_number:
        number = subprocess.check_output(
            ["gcloud", "projects", "describe", settings.project_id, "--format=value(projectNumber)"],
            text=True,
        ).strip()
        if number:
            os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"] = number
            get_settings.cache_clear()
            settings = get_settings()
    mcp_url = os.environ.get("MCP_TOOLS_URL") or settings.mcp_tools_url
    if not mcp_url:
        raise SystemExit("MCP_TOOLS_URL is required")

    os.environ["MCP_TOOLS_URL"] = mcp_url
    os.environ["VERTEX_LOCATION"] = settings.vertex_location
    os.environ["VERTEX_MODEL"] = settings.vertex_model
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    # Factory forces this to global for gemini-3.5-flash; keep that for pickle time.
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.vertex_location

    from agentplatform import Client
    from agentplatform._genai.types.common import IdentityType
    from permit_pilot.agents._runtime import wrap_for_runtime

    client = Client(project=settings.project_id, location=settings.region)
    existing = _existing_by_display_name(client)

    with tempfile.TemporaryDirectory(prefix="permit-fleet-wheels-") as tmp:
        pack_dir = Path(tmp)
        wheels = _build_wheels(pack_dir)
        # Agent Runtime extracts extra_packages at /code. Filenames in the
        # tarball must be basenames or pip looks for /code/<wheel> and misses
        # nested Mac temp paths.
        os.chdir(pack_dir)
        extra_packages = [path.name for path in wheels]
        requirements = extra_packages + [
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-adk[a2a]",
            "a2a-sdk[http-server]>=0.3.4,<2",
            "cloudpickle",
            "mcp>=1.9,<2",
            "pydantic-settings",
            "google-auth",
            "httpx",
            "pydantic",
        ]

        mapping: dict[str, str] = {}
        engines_seed = ROOT / ".agent-engines.json"
        if engines_seed.exists():
            try:
                mapping.update(json.loads(engines_seed.read_text()) or {})
            except json.JSONDecodeError:
                pass
        fleet_names = {agent.name for agent in FLEET}
        for spec_name, resource in existing.items():
            if spec_name in fleet_names:
                mapping.setdefault(spec_name, str(resource).rsplit("/", 1)[-1])
        mapping = {name: engine_id for name, engine_id in mapping.items() if name in fleet_names}
        identities: dict[str, dict[str, str]] = {}
        failures: list[str] = []
        only = os.environ.get("DEPLOY_ONLY", "").strip()
        fleet = [agent for agent in FLEET if not only or agent.name == only]
        if not fleet:
            raise SystemExit(f"DEPLOY_ONLY={only} matched no agents")

        env_vars = {
            key: value
            for key, value in _stringify_env(
                {
                    "GOOGLE_CLOUD_PROJECT_NUMBER": settings.project_number
                    or os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", ""),
                    "VERTEX_LOCATION": settings.vertex_location,
                    "VERTEX_MODEL": settings.vertex_model,
                    "GOOGLE_GENAI_USE_VERTEXAI": "true",
                    "MCP_TOOLS_URL": mcp_url,
                    "MCP_INVOKER_SERVICE_ACCOUNT": f"permit-pilot-api@{settings.project_id}.iam.gserviceaccount.com",
                    "GOOGLE_API_USE_CLIENT_CERTIFICATE": "false",
                    "GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES": "false",
                    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
                    "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_latest_experimental",
                    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "EVENT_ONLY",
                }
            ).items()
            if value
        }

        for spec in fleet:
            if mapping:
                env_vars["AGENT_ENGINE_IDS"] = ",".join(f"{k}={v}" for k, v in mapping.items())
            for name, engine_id in mapping.items():
                env_vars[f"{name.upper()}_ENGINE_ID"] = engine_id
            print(f"Deploying {spec.name}...", flush=True)
            module_name = MODULE_BY_AGENT.get(
                spec.name, spec.name.replace("_agent", "")
            )
            import importlib

            importlib.invalidate_caches()
            mod = importlib.import_module(f"permit_pilot.agents.{module_name}.agent")
            local_agent = mod.root_agent
            adk_app = wrap_for_runtime(local_agent)
            try:
                import cloudpickle

                cloudpickle.dumps(adk_app)
            except Exception as exc:  # noqa: BLE001
                if spec.name == "permit_orchestrator" and not os.environ.get(
                    "PERMIT_PILOT_INPROCESS_SPECIALISTS"
                ):
                    print(
                        f"  RemoteA2aAgent pickle failed ({exc}); "
                        "rebuilding coordinator with in-process specialists",
                        flush=True,
                    )
                    os.environ["PERMIT_PILOT_INPROCESS_SPECIALISTS"] = "1"
                    importlib.invalidate_caches()
                    import permit_pilot.agents._factory as factory_mod
                    importlib.reload(factory_mod)
                    import permit_pilot.agents.orchestrator.agent as orch_mod
                    importlib.reload(orch_mod)
                    local_agent = orch_mod.root_agent
                    adk_app = wrap_for_runtime(local_agent)
                else:
                    raise
            config = {
                "display_name": spec.name,
                "description": spec.description,
                "identity_type": IdentityType.AGENT_IDENTITY,
                "requirements": requirements,
                "extra_packages": extra_packages,
                "staging_bucket": settings.staging_bucket_uri,
                "env_vars": env_vars,
                "min_instances": 0,
                "max_instances": 1,
            }
            try:
                if spec.name in existing:
                    remote = client.agent_engines.update(
                        name=existing[spec.name],
                        agent=adk_app,
                        config=config,
                    )
                    action = "updated"
                else:
                    remote = client.agent_engines.create(agent=adk_app, config=config)
                    action = "created"
                name = getattr(remote, "api_resource", remote).name
                engine_id = name.rsplit("/", 1)[-1]
                detail = client.agent_engines.get(name=name)
                identity = _effective_identity(detail)
                num = settings.project_number or os.environ.get(
                    "GOOGLE_CLOUD_PROJECT_NUMBER", ""
                )
                constructed = (
                    f"agents.global.proj-{num}.system.id.goog/resources/"
                    f"aiplatform/projects/{num}/locations/{settings.region}/"
                    f"reasoningEngines/{engine_id}"
                )
                mapping[spec.name] = engine_id
                identities[spec.name] = {
                    "engine_id": engine_id,
                    "resource_name": name,
                    "effective_identity": identity or constructed,
                    "identity_type": "AGENT_IDENTITY",
                    "spiffe": constructed,
                }
                print(f"  {action} {spec.name} -> {engine_id}", flush=True)
                print(f"  SPIFFE {constructed}", flush=True)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{spec.name}: {exc}")
                print(f"  FAILED {spec.name}: {exc}", flush=True)
                break
        os.chdir(ROOT)

    engines_path = ROOT / ".agent-engines.json"
    merged = {}
    if engines_path.exists():
        try:
            merged = json.loads(engines_path.read_text()) or {}
        except json.JSONDecodeError:
            merged = {}
    merged.update(mapping)
    mapping = merged
    ident_path = ROOT / ".agent-identities.json"
    merged_ident = {}
    if ident_path.exists():
        try:
            merged_ident = json.loads(ident_path.read_text()) or {}
        except json.JSONDecodeError:
            merged_ident = {}
    merged_ident.update(identities)
    identities = merged_ident

    engines_path.write_text(json.dumps(mapping, indent=2) + "\n")
    ident_path.write_text(json.dumps(identities, indent=2) + "\n")
    _write_env_keys(mapping)
    csv = ",".join(f"{k}={v}" for k, v in mapping.items())
    print(f"AGENT_ENGINE_IDS={csv}")
    if "permit_orchestrator" in mapping:
        print(f"ORCHESTRATOR_ENGINE_ID={mapping['permit_orchestrator']}")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(f" - {item}")
        raise SystemExit(1)
    if only:
        print(f"partial deploy complete: {', '.join(a.name for a in fleet)}")
        return
    if len(mapping) != len(FLEET):
        raise SystemExit("Not all fleet agents were deployed")
    print("fleet deploy complete")


if __name__ == "__main__":
    main()
