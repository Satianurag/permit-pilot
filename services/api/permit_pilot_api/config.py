from permit_pilot_core.settings import get_settings


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
    observability = (
        f"https://console.cloud.google.com/vertex-ai/agents?project={project_id}" if project_id else None
    )
    return {
        "cloud_trace_url": cloud_trace,
        "topology_url": topology,
        "agent_gateway_url": gateway,
        "agent_registry_url": registry,
        "model_armor_url": armor,
        "agent_observability_url": observability,
        "langfuse_url": None,
        "gcp_workflows_url": None,
        "case_id": case_id,
    }
