from __future__ import annotations

import os
from pathlib import Path

from permit_pilot_core.settings import get_settings


def _orchestrator_registry_agent_uid() -> str:
    """Resolve Agent Registry agent id for permit_orchestrator (GEAP Traces tab lives here)."""
    explicit = os.environ.get("ORCHESTRATOR_REGISTRY_AGENT_UID", "").strip()
    if explicit:
        return explicit
    try:
        root = Path(__file__).resolve().parents[3]
        ident_path = root / ".agent-identities.json"
        if ident_path.exists():
            import json

            identities = json.loads(ident_path.read_text()) or {}
            row = identities.get("permit_orchestrator") or {}
            uid = row.get("registry_agent_uid") or row.get("registry_agent_id") or ""
            if uid:
                return str(uid).rsplit("/", 1)[-1]
    except Exception:
        pass
    return ""


def gcp_project_id() -> str:
    return get_settings().project_id


def cloud_service_url() -> str:
    return get_settings().permit_pilot_url.rstrip("/")


def seed_on_startup() -> bool:
    return get_settings().seed_on_startup


def cors_origins() -> list[str]:
    origins = get_settings().cors_origin_list
    if origins:
        return origins
    url = cloud_service_url()
    return [url] if url else []


def observability_links(*, case_id: str | None, project_id: str) -> dict[str, str | None]:
    settings = get_settings()
    location = settings.region
    cloud_trace = f"https://console.cloud.google.com/traces/list?project={project_id}" if project_id else None
    topology = (
        f"https://console.cloud.google.com/gen-app-builder/engines?project={project_id}"
        if project_id
        else None
    )
    gateway = None
    if settings.agent_gateway_name and project_id:
        gateway = (
            f"https://console.cloud.google.com/net-services/agent-gateway/details/"
            f"{location}/{settings.agent_gateway_name}?project={project_id}"
        )
    registry = (
        f"https://console.cloud.google.com/vertex-ai/agents/registry?project={project_id}"
        if project_id
        else None
    )
    armor = (
        f"https://console.cloud.google.com/security/model-armor/locations/{settings.model_armor_location}"
        f"/templates/{settings.model_armor_template}?project={project_id}"
        if project_id
        else None
    )
    orchestrator_id = settings.orchestrator_engine_id or settings.engine_id_map.get("permit_orchestrator")
    registry_uid = _orchestrator_registry_agent_uid()
    agent_observability = None
    if registry_uid and project_id:
        # GEAP Agent Observability Traces tab is on the Agent Registry agent detail page.
        agent_observability = (
            f"https://console.cloud.google.com/vertex-ai/agents/locations/{location}/"
            f"agents/{registry_uid}?project={project_id}"
        )
    elif orchestrator_id and project_id:
        agent_observability = (
            f"https://console.cloud.google.com/vertex-ai/agents/registry?project={project_id}"
        )
    elif project_id:
        agent_observability = f"https://console.cloud.google.com/vertex-ai/agents/registry?project={project_id}"

    return {
        "cloud_trace_url": cloud_trace,
        "topology_url": topology,
        "agent_gateway_url": gateway,
        "agent_registry_url": registry,
        "model_armor_url": armor,
        "agent_observability_url": agent_observability,
        "case_id": case_id,
    }
