from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
    create_mcp_http_client,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from permit_pilot_core.platform.fleet import fleet_by_name
from permit_pilot_core.settings import get_settings


def _mcp_url() -> str:
    settings = get_settings()
    url = (os.environ.get("MCP_TOOLS_URL") or settings.mcp_tools_url).rstrip("/")
    if not url:
        raise RuntimeError("MCP_TOOLS_URL is required for fleet agents")
    if not url.endswith("/mcp"):
        url = f"{url}/mcp"
    return url


def _audience() -> str:
    url = _mcp_url()
    return url[:-4] if url.endswith("/mcp") else url


_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_TOKEN_TTL_SECONDS = 50 * 60


def _identity_headers(_ctx: Any = None) -> dict[str, str]:
    """Google-signed OIDC identity token for Cloud Run MCP.

    Agent Identity SPIFFE tokens are rejected by Cloud Run (401 token could
    not be verified). Prefer the metadata identity endpoint, which returns a
    Google-signed token for the runtime service agent when token sharing is
    allowed.
    """
    audience = _audience()
    cached = _TOKEN_CACHE.get(audience)
    if cached and cached[1] > time.time():
        return {"Authorization": f"Bearer {cached[0]}"}
    token = _mint_google_id_token(audience)
    if not token:
        raise RuntimeError("Could not mint an identity token for the MCP server")
    _TOKEN_CACHE[audience] = (token, time.time() + _TOKEN_TTL_SECONDS)
    return {"Authorization": f"Bearer {token}"}


def _mint_google_id_token(audience: str) -> str:
    from urllib.parse import quote
    from urllib.request import Request as UrlRequest
    from urllib.request import urlopen

    metadata = (
        "http://metadata.google.internal/computeMetadata/v1/instance/"
        f"service-accounts/default/identity?audience={quote(audience, safe='')}"
        "&format=full"
    )
    try:
        req = UrlRequest(metadata, headers={"Metadata-Flavor": "Google"})
        with urlopen(req, timeout=5) as resp:
            token = resp.read().decode().strip()
            if token:
                return token
    except Exception:
        pass
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        return id_token.fetch_id_token(Request(), audience)
    except Exception:
        pass
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"],
            text=True,
        ).strip()
    except Exception:
        return ""


def _mcp_http_client_factory(headers=None, timeout=None, auth=None):
    """Inject a fresh identity token on every MCP HTTP client construction.

    ADK only invokes header_provider when a ReadonlyContext exists, so listing
    tools (and Agent Runtime startup) would otherwise hit Cloud Run with 403.
    This factory is a module-level function so it pickles by reference.
    """
    merged = dict(headers or {})
    merged.update(_identity_headers())
    return create_mcp_http_client(headers=merged, timeout=timeout, auth=auth)


def build_agent(name: str) -> Agent:
    settings = get_settings()
    spec = fleet_by_name()[name]
    mcp_url = _mcp_url()
    # gemini-3.5-flash is served at global, not us-central1.
    os.environ["VERTEX_LOCATION"] = settings.vertex_location
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.vertex_location
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    os.environ.setdefault("VERTEX_MODEL", settings.vertex_model)
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=mcp_url,
            timeout=30.0,
            sse_read_timeout=120.0,
            httpx_client_factory=_mcp_http_client_factory,
        ),
        tool_filter=list(spec.tools),
        header_provider=_identity_headers,
    )
    return Agent(
        name=spec.name,
        model=settings.vertex_model,
        description=spec.description,
        instruction=spec.instruction,
        tools=[toolset],
    )
