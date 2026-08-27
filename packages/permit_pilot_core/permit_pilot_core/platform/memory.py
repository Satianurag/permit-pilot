from __future__ import annotations

from typing import Any

from google.auth import default
from google.auth.transport.requests import Request
import httpx

from permit_pilot_core.platform.runtime import engine_resource
from permit_pilot_core.settings import get_settings


def _token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _engine_url(engine_id: str | None = None) -> str:
    settings = get_settings()
    engine = engine_id or settings.orchestrator_engine_id
    if not engine:
        raise RuntimeError("ORCHESTRATOR_ENGINE_ID is required for Memory Bank")
    name = engine_resource(engine)
    return f"https://{settings.region}-aiplatform.googleapis.com/v1beta1/{name}"


def create_fact(*, bbl: str, fact: str, engine_id: str | None = None) -> dict[str, Any]:
    """Store a parcel-scoped fact in Memory Bank."""
    settings = get_settings()
    engine = engine_id or settings.orchestrator_engine_id
    if not engine:
        raise RuntimeError("ORCHESTRATOR_ENGINE_ID is required for Memory Bank")
    try:
        from agentplatform import Client
    except ImportError:  # pragma: no cover
        from vertexai import Client  # type: ignore
    client = Client(project=settings.project_id, location=settings.region)
    name = engine_resource(engine)
    op = client.agent_engines.memories.create(name=name, fact=fact, scope={"bbl": bbl})
    response = getattr(op, "response", op)
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return {"fact": fact, "scope": {"bbl": bbl}, "name": getattr(response, "name", str(response))}


def generate_from_session(*, session: str, bbl: str, engine_id: str | None = None) -> dict[str, Any]:
    url = f"{_engine_url(engine_id)}/memories:generate"
    response = httpx.post(
        url,
        headers=_headers(),
        json={
            "vertexSessionSource": {"session": session},
            "scope": {"bbl": bbl},
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def retrieve(*, bbl: str, query: str | None = None, engine_id: str | None = None) -> list[dict[str, Any]]:
    url = f"{_engine_url(engine_id)}/memories:retrieve"
    body: dict[str, Any] = {"scope": {"bbl": bbl}}
    if query:
        body["similaritySearchParams"] = {"searchQuery": query, "topK": 8}
    response = httpx.post(url, headers=_headers(), json=body, timeout=60.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    retrieved = payload.get("retrievedMemories") or payload.get("memories") or payload.get("output") or []
    if isinstance(retrieved, list):
        return retrieved
    return [retrieved]


def list_memories(*, engine_id: str | None = None) -> list[dict[str, Any]]:
    url = f"{_engine_url(engine_id)}/memories"
    response = httpx.get(url, headers=_headers(), timeout=60.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("memories") or payload.get("agentEngineMemories") or [])
