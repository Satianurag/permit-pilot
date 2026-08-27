from __future__ import annotations

import json
from typing import Any, Iterator

from google.auth import default
from google.auth.transport.requests import Request
import httpx

from permit_pilot_core.settings import get_settings


def _token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def engine_resource(engine_id: str) -> str:
    settings = get_settings()
    if engine_id.startswith("projects/"):
        return engine_id
    return (
        f"projects/{settings.project_id}/locations/{settings.region}/reasoningEngines/{engine_id}"
    )


def _query_url(engine_id: str) -> str:
    settings = get_settings()
    name = engine_resource(engine_id)
    return f"https://{settings.region}-aiplatform.googleapis.com/v1/{name}:query"


def stream_query(*, engine_id: str, user_id: str, message: str) -> list[dict[str, Any]]:
    """Run a deployed Agent Runtime query and collect events."""
    payload = {
        "classMethod": "stream_query",
        "input": {
            "user_id": user_id,
            "message": message,
        },
    }
    response = httpx.post(
        _query_url(engine_id),
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180.0,
    )
    if response.status_code >= 400:
        # Alternate method name used by some Agent Engine revisions.
        payload["classMethod"] = "async_stream_query"
        response = httpx.post(
            _query_url(engine_id),
            headers={
                "Authorization": f"Bearer {_token()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180.0,
        )
    response.raise_for_status()
    body = response.json()
    output = body.get("output") or body.get("response") or body
    if isinstance(output, list):
        return output
    if isinstance(output, dict) and "output" in output:
        inner = output["output"]
        return inner if isinstance(inner, list) else [inner]
    return [output]


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
    return "\n".join(chunks).strip()


def iter_json_lines(text: str) -> Iterator[dict[str, Any]]:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
