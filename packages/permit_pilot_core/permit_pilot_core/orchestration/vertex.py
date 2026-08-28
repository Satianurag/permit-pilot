from __future__ import annotations

from google import genai

from permit_pilot_core.models import Case, DepartmentReview


def orchestrate_case_summary(case: Case, reviews: list[DepartmentReview]) -> str:
    """Briefing fallback via Vertex Gemini when Agent Runtime is unavailable."""
    from permit_pilot_core.platform.armor import sanitize_model_response, sanitize_user_prompt
    from permit_pilot_core.settings import get_settings

    settings = get_settings()
    project = settings.project_id
    location = settings.vertex_location
    model_id = settings.vertex_model

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
    inbound = sanitize_user_prompt(prompt)
    if inbound.blocked:
        raise RuntimeError("Model Armor blocked the clerk briefing prompt")
    response = client.models.generate_content(model=model_id, contents=prompt)
    text = (response.text or "").strip()
    outbound = sanitize_model_response(text)
    if outbound.blocked:
        raise RuntimeError("Model Armor blocked the clerk briefing response")
    return text
