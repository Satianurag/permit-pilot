from __future__ import annotations

from permit_pilot_core.settings import get_settings


def agent_spiffe(
    engine_id: str,
    *,
    project_number: str | None = None,
    location: str | None = None,
) -> str:
    """SPIFFE path for an Agent Runtime engine (proj- trust domain, not project-)."""
    if project_number is None or location is None:
        settings = get_settings()
        number = settings.project_number if project_number is None else project_number
        loc = settings.region if location is None else location
    else:
        number = project_number
        loc = location
    if not engine_id or not number:
        return ""
    return (
        f"agents.global.proj-{number}.system.id.goog/resources/"
        f"aiplatform/projects/{number}/locations/{loc}/reasoningEngines/{engine_id}"
    )


def agent_iap_principal(
    engine_id: str,
    *,
    project_number: str | None = None,
    location: str | None = None,
) -> str:
    spiffe = agent_spiffe(engine_id, project_number=project_number, location=location)
    return f"principal://{spiffe}" if spiffe else ""
