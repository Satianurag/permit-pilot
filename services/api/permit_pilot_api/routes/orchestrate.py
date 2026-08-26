from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.observability.traces import TraceRecorder
from permit_pilot_core.orchestration.vertex import orchestrate_case_summary
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/cases", tags=["orchestrate"], dependencies=[Depends(get_current_user)])


@router.get("/{case_id}/trace")
def get_trace(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_trace_spans(case_id)


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

    trace = TraceRecorder(store, case_id)
    try:
        with trace.span("vertex.briefing", actor=clerk_actor(current_user), detail="Clerk briefing generation"):
            summary = orchestrate_case_summary(case, reviews)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Briefing generation failed: {exc}") from exc

    store.save_briefing(
        case_id,
        summary=summary,
        model="vertex",
        generated_by=clerk_actor(current_user),
    )
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="briefing_generated",
        detail=summary[:200] + ("…" if len(summary) > 200 else ""),
    )
    return {"case_id": case_id, "summary": summary, "model": "vertex"}
