"""Clerk briefing from persisted reviews. Not a second distribution product.

Prefers the Agent Runtime orchestrator; falls back to Vertex Gemini via orchestration.vertex.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.fleet_runner import invoke_orchestrator
from permit_pilot_core.orchestration.vertex import orchestrate_case_summary
from permit_pilot_core.settings import get_settings
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/cases", tags=["orchestrate"], dependencies=[Depends(get_current_user)])


@router.post("/{case_id}/orchestrate")
def orchestrate(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    reviews = store.list_distribution(case_id)
    if not reviews:
        raise HTTPException(status_code=409, detail="Run distribution before generating a briefing")

    settings = get_settings()
    summary = ""
    generated_by = "briefing_agent"
    if settings.orchestrator_engine_id:
        try:
            summary = invoke_orchestrator(
                store,
                case_id=case_id,
                user_id=current_user.username,
                instruction=(
                    "Do not re-run department specialists. Write a 3-sentence clerk briefing "
                    "from persisted reviews only."
                ),
            )
            generated_by = "permit_orchestrator"
        except Exception:
            summary = ""
    if not summary:
        try:
            summary = orchestrate_case_summary(case, reviews)
            generated_by = "briefing_fallback"
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Briefing generation failed: {exc}") from exc

    store.save_briefing(
        case_id,
        summary=summary,
        model=settings.vertex_model,
        generated_by=generated_by,
    )
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="briefing_generated",
        detail=summary[:200] + ("…" if len(summary) > 200 else ""),
    )
    return {"case_id": case_id, "summary": summary, "model": settings.vertex_model}
