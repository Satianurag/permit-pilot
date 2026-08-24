from __future__ import annotations

import os

from google import genai

from permit_pilot_core.models import Case, DepartmentReview


def orchestrate_case_summary(case: Case, reviews: list[DepartmentReview]) -> str:
    """Clerk briefing via Vertex Gemini (google-genai SDK, Context7-current)."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_id = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")

    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex orchestration")

    client = genai.Client(vertexai=True, project=project, location=location)
    dept_lines = "\n".join(f"- {r.department.value}: {r.status.value} — {r.summary}" for r in reviews)
    prompt = (
        f"You are the NYC permit orchestrator assisting clerk review.\n"
        f"Case: {case.address} (BBL {case.bbl}, BIN {case.bin or 'n/a'})\n"
        f"Work: {case.work_type}\n\n"
        f"Department distribution results:\n{dept_lines}\n\n"
        f"Write a concise 3-sentence clerk briefing: risks, blockers, and recommended next action. "
        f"Only cite facts from the department results above."
    )
    response = client.models.generate_content(model=model_id, contents=prompt)
    return (response.text or "").strip()
