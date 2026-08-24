from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.auth import get_current_user
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/cases", tags=["workflow"])


@router.get("/{case_id}/workflow", dependencies=[Depends(get_current_user)])
def get_workflow(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store)
    return runner.get_steps(case_id)


@router.post("/{case_id}/workflow/resume")
async def resume_workflow(case_id: str, request: Request):
    """Resume distribution workflow. Called by GCP Cloud Workflows with OIDC auth."""
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store, engine)
    step = await runner.run_next(case.id, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    store.append_audit(case_id, actor="system", action="workflow_resumed", detail="Distribution workflow resumed")
    return {"step": step, "steps": runner.get_steps(case_id)}
