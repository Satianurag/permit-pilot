"""Gemma 3 packet completeness scan. Falls back to identifier-only scan if the model is unavailable."""

from __future__ import annotations

import json
import logging
from typing import Any

from permit_pilot_core.settings import get_settings

logger = logging.getLogger(__name__)

GEMMA_MODELS = (
    "gemma-3-4b-it",
    "gemma-3-12b-it",
    "publishers/google/models/gemma-3-4b-it",
)


def scan_packet_with_gemma(packet_text: str) -> dict[str, Any]:
    """Return {complete_enough, findings, missing, model} from Gemma, or empty dict on failure."""
    text = packet_text.strip()
    if not text:
        return {"complete_enough": True, "findings": [], "missing": [], "model": ""}
    settings = get_settings()
    prompt = (
        "You extract completeness of an NYC building-permit intake packet. "
        "Return JSON only with keys complete_enough (bool), missing (list of strings), findings (list of strings). "
        "Flag missing BIN, BBL, work type, or applicant identity. Do not invent facts.\n\n"
        f"Packet:\n{text[:6000]}"
    )
    last_error = ""
    for model_id in GEMMA_MODELS:
        try:
            from google import genai

            client = genai.Client(vertexai=True, project=settings.project_id, location=settings.vertex_location)
            response = client.models.generate_content(model=model_id, contents=prompt)
            raw = (response.text or "").strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end <= start:
                continue
            parsed = json.loads(raw[start : end + 1])
            return {
                "complete_enough": bool(parsed.get("complete_enough", True)),
                "findings": list(parsed.get("findings") or []),
                "missing": list(parsed.get("missing") or []),
                "model": model_id,
            }
        except Exception as exc:  # noqa: BLE001 — try next publisher id
            last_error = str(exc)
            logger.warning("Gemma model %s unavailable: %s", model_id, exc)
    logger.warning("Gemma packet scan skipped: %s", last_error)
    return {"complete_enough": True, "findings": ["Gemma unavailable — identifier scan only"], "missing": [], "model": ""}
