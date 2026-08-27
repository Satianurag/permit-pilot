from __future__ import annotations

import json
from typing import Any, Iterator

from google.auth import default
from google.auth.transport.requests import Request
import httpx

from permit_pilot_core.settings import get_settings


def engine_resource(engine_id: str) -> str:
    settings = get_settings()
    if engine_id.startswith("projects/"):
        return engine_id
    return (
        f"projects/{settings.project_id}/locations/{settings.region}/reasoningEngines/{engine_id}"
    )


def _token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _parse_stream_events(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    stripped = text.strip()
    if not stripped:
        return events
    if stripped.startswith("{"):
        try:
            events.append(json.loads(stripped))
            return events
        except json.JSONDecodeError:
            pass
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def stream_query(*, engine_id: str, user_id: str, message: str) -> list[dict[str, Any]]:
    """Run a deployed Agent Runtime query via the streamQuery REST API."""
    settings = get_settings()
    name = engine_resource(engine_id)
    url = f"https://{settings.region}-aiplatform.googleapis.com/v1/{name}:streamQuery?alt=sse"
    payload = {
        "classMethod": "stream_query",
        "input": {"user_id": user_id, "message": message},
    }
    response = httpx.post(url, headers=_headers(), json=payload, timeout=300.0)
    response.raise_for_status()
    return _parse_stream_events(response.text)


def extract_text(events: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for event in events:
        if isinstance(event, str):
            chunks.append(event)
            continue
        content = event.get("content") or event.get("text") or ""
        if isinstance(content, dict):
            parts = content.get("parts") or []
            for part in parts:
                if isinstance(part, dict) and part.get("text"):
                    chunks.append(str(part["text"]))
        elif content:
            chunks.append(str(content))
        text = event.get("text")
        if text and not content:
            chunks.append(str(text))
    return "\n".join(chunks).strip()


def iter_json_lines(text: str) -> Iterator[dict[str, Any]]:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
