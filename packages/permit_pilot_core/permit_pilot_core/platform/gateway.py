"""Clerk Agent Gateway invoke fingerprints. Allowlist is HMAC of the agent name, not admin role."""

from __future__ import annotations

import hashlib
import hmac

from permit_pilot_core.settings import get_settings


def _secret() -> bytes:
    settings = get_settings()
    raw = (settings.auth_secret_key or "permit-pilot-gateway-allowlist").encode()
    return raw


def signed_fingerprint(agent_name: str) -> str:
    """Deterministic fingerprint clerks present on a valid Agent Runtime invoke."""
    return hmac.new(_secret(), f"invoke:{agent_name}".encode(), hashlib.sha256).hexdigest()[:24]


def fingerprint_allowed(agent_name: str, fingerprint: str) -> bool:
    expected = signed_fingerprint(agent_name)
    provided = (fingerprint or "").strip()
    if not provided or len(provided) != len(expected):
        return False
    return hmac.compare_digest(expected, provided)
