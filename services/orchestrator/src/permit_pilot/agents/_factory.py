from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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
    """Google-signed OIDC identity token for Cloud Run MCP."""
    audience = _audience()
    cached = _TOKEN_CACHE.get(audience)
    if cached and cached[1] > time.time():
        return {"Authorization": f"Bearer {cached[0]}"}
    token = _mint_google_id_token(audience)
    if not token:
        raise RuntimeError(
            f"Could not mint an identity token for MCP audience {audience}. "
            "Ensure Agent Runtime token sharing is enabled or metadata identity is available."
        )
    _TOKEN_CACHE[audience] = (token, time.time() + _TOKEN_TTL_SECONDS)
    return {"Authorization": f"Bearer {token}"}


def _invoker_service_account() -> str:
    explicit = os.environ.get("MCP_INVOKER_SERVICE_ACCOUNT", "").strip()
    if explicit:
        return explicit
    settings = get_settings()
    return f"permit-pilot-api@{settings.project_id}.iam.gserviceaccount.com"


def _mint_via_service_account_impersonation(audience: str) -> str:
    """Agent Identity must impersonate a SA to get a Cloud Run-compatible ID token."""
    import httpx
    from google.auth import default
    from google.auth.transport.requests import Request

    invoker_sa = _invoker_service_account()
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    url = (
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
        f"{invoker_sa}:generateIdToken"
    )
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        },
        json={"audience": audience, "includeEmail": True},
        timeout=30.0,
    )
    if response.status_code >= 400:
        logger.warning(
            "generateIdToken failed for %s audience %s: %s %s",
            invoker_sa,
            audience,
            response.status_code,
            response.text[:300],
        )
        return ""
    token = str(response.json().get("token") or "").strip()
    if token:
        logger.debug("Minted MCP ID token via generateIdToken(%s)", invoker_sa)
    return token


def _mint_google_id_token(audience: str) -> str:
    token = _mint_via_service_account_impersonation(audience)
    if token:
        return token

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
                logger.debug("Minted MCP identity token via metadata server")
                return token
    except Exception as exc:
        logger.warning("Metadata identity token mint failed for %s: %s", audience, exc)

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        token = id_token.fetch_id_token(Request(), audience)
        if token:
            logger.debug("Minted MCP identity token via google.oauth2.id_token")
            return token
    except Exception as exc:
        logger.warning("google.oauth2 id_token fetch failed for %s: %s", audience, exc)

    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token", f"--audiences={audience}"],
            text=True,
        ).strip()
        if token:
            logger.debug("Minted MCP identity token via gcloud CLI")
            return token
    except Exception as exc:
        logger.warning("gcloud print-identity-token failed: %s", exc)

    return ""


def _mcp_http_client_factory(headers=None, timeout=None, auth=None):
    """Inject a fresh identity token on every MCP HTTP client construction."""
    merged = dict(headers or {})
    merged.update(_identity_headers())
    return create_mcp_http_client(headers=merged, timeout=timeout, auth=auth)


def build_agent(name: str) -> Agent:
    settings = get_settings()
    spec = fleet_by_name()[name]
    mcp_url = _mcp_url()
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
