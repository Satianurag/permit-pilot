from __future__ import annotations

import hashlib
import os


def trusted_agent_fingerprints() -> set[str]:
    raw = os.environ.get("AGENT_TRUSTED_FINGERPRINTS", "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def agent_fingerprint(agent_name: str) -> str:
    digest = hashlib.sha256(f"permit-pilot:{agent_name}".encode()).hexdigest()
    return digest[:16]


def verify_agent_signature(agent_name: str, signature: str | None) -> bool:
    if not signature:
        return False
    expected = agent_fingerprint(agent_name)
    return signature == expected and expected in trusted_agent_fingerprints()
