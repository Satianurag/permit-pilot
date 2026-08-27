from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.platform.tasks import enqueue_distribution
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/cases", tags=["fleet"], dependencies=[Depends(get_current_user)])


@router.post("/{case_id}/fleet/run")
async def run_fleet(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        task_name = enqueue_distribution(case_id=case_id, reason="clerk")
        store.append_audit(
            case_id,
            actor=clerk_actor(current_user),
            action="fleet_enqueued",
            detail=task_name,
        )
        return {"queued": True, "task": task_name}
    except Exception as exc:
        store.append_audit(
            case_id,
            actor=clerk_actor(current_user),
            action="fleet_enqueue_failed",
            detail=str(exc),
        )
        raise HTTPException(status_code=503, detail="Cloud Tasks enqueue failed") from exc
