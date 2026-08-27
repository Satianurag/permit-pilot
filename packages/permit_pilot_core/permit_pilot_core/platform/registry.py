from __future__ import annotations

import json
from typing import Any

from google.auth import default
from google.auth.transport.requests import Request
import httpx

from permit_pilot_core.settings import get_settings


def _token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _registry_root() -> str:
    settings = get_settings()
    return f"https://agentregistry.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.region}"


def list_agents() -> list[dict[str, Any]]:
    url = f"{_registry_root()}/agents"
    response = httpx.get(url, headers=_headers(), timeout=30.0)
    response.raise_for_status()
    return list(response.json().get("agents") or response.json().get("agent") or [])


def list_mcp_servers() -> list[dict[str, Any]]:
    url = f"{_registry_root()}/mcpServers"
    response = httpx.get(url, headers=_headers(), timeout=30.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("mcpServers") or payload.get("mcp_servers") or [])


def list_endpoints() -> list[dict[str, Any]]:
    url = f"{_registry_root()}/endpoints"
    response = httpx.get(url, headers=_headers(), timeout=30.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("endpoints") or [])


def list_services() -> list[dict[str, Any]]:
    url = f"{_registry_root()}/services"
    response = httpx.get(url, headers=_headers(), timeout=30.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("services") or [])


def catalog() -> dict[str, Any]:
    try:
        agents = list_agents()
        if not agents:
            agents = list_services()
        return {
            "agents": agents,
            "mcp_servers": list_mcp_servers(),
            "endpoints": list_endpoints(),
            "registry": _registry_root(),
        }
    except Exception as exc:  # noqa: BLE001 — live registry is optional for clerk fleet cards
        return {
            "agents": [],
            "mcp_servers": [],
            "endpoints": [],
            "registry": _registry_root(),
            "error": str(exc),
        }


def dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str)
