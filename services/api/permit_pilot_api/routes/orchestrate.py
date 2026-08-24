from fastapi import APIRouter, HTTPException, Request

from permit_pilot_core.observability.traces import TraceRecorder
from permit_pilot_core.orchestration.vertex import orchestrate_case_summary
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/cases", tags=["orchestrate"])


@router.get("/{case_id}/trace")
def get_trace(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_trace_spans(case_id)


@router.post("/{case_id}/orchestrate")
def orchestrate(case_id: str, request: Request):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    reviews = store.list_distribution(case_id)
    if not reviews:
        raise HTTPException(status_code=409, detail="Run distribution workflow first")

    trace = TraceRecorder(store, case_id)
    try:
        with trace.span("vertex.orchestrator", actor="permit_orchestrator", detail="Gemini clerk briefing"):
            summary = orchestrate_case_summary(case, reviews)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Vertex orchestration failed: {exc}") from exc

    store.append_audit(case_id, actor="permit_orchestrator", action="orchestration_complete", detail=summary)
    return {"case_id": case_id, "summary": summary, "model": "vertex"}
