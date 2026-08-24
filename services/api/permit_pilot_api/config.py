import os


def gcp_project_id() -> str:
    return os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0233250350")


def seed_on_startup() -> bool:
    return os.environ.get("SEED_ON_STARTUP", "false").lower() in {"1", "true", "yes"}


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def observability_links(*, case_id: str | None, project_id: str) -> dict[str, str | None]:
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    langfuse_host = os.environ.get("LANGFUSE_HOST")
    langfuse_project = os.environ.get("LANGFUSE_PROJECT_ID")
    cloud_trace = (
        f"https://console.cloud.google.com/traces/list?project={project_id}"
        if project_id
        else None
    )
    langfuse_url = None
    if langfuse_host and case_id:
        base = langfuse_host.rstrip("/")
        if langfuse_project:
            langfuse_url = f"{base}/project/{langfuse_project}/traces?search={case_id}"
        else:
            langfuse_url = f"{base}/traces?search={case_id}"
    workflows_url = None
    workflow_name = os.environ.get("GCP_WORKFLOW_NAME")
    if workflow_name and project_id:
        workflows_url = (
            f"https://console.cloud.google.com/workflows/workflow/"
            f"{location}/{workflow_name}/executions?project={project_id}"
        )
    return {
        "cloud_trace_url": cloud_trace,
        "langfuse_url": langfuse_url,
        "gcp_workflows_url": workflows_url,
    }
