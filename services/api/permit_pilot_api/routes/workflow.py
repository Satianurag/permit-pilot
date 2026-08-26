from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.orchestration.gcp_workflows import gcp_workflows_enabled, start_distribution_workflow
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user, get_workflow_resume_caller
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
async def resume_workflow(
    case_id: str,
    request: Request,
    caller: Annotated[ClerkUser, Depends(get_workflow_resume_caller)],
):
    """Resume distribution workflow. Clerk JWT or Cloud Workflows OIDC."""
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store, engine)
    step = await runner.resume_next(case.id, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    actor = clerk_actor(caller) if caller.username != "workflow" else "Cloud Workflows"
    store.append_audit(case_id, actor=actor, action="workflow_resumed", detail="Distribution workflow resumed")
    return {"step": step, "steps": runner.get_steps(case_id)}


@router.post("/{case_id}/workflow/gcp-run", dependencies=[Depends(get_current_user)])
def start_gcp_workflow(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not gcp_workflows_enabled():
        raise HTTPException(status_code=503, detail="GCP Cloud Workflows is not configured on this deployment")
    api_base = str(request.base_url).rstrip("/")
    execution_id = start_distribution_workflow(case_id=case_id, api_base=api_base)
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="gcp_workflow_started",
        detail=f"Cloud Workflows execution {execution_id}",
    )
    return {"execution_id": execution_id, "case_id": case_id}


@router.post("/{case_id}/workflow/interrupt", dependencies=[Depends(get_current_user)])
def interrupt_workflow(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    """Demo beat: simulate a worker kill mid-run."""
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store)
    step = runner.mark_interrupted(case_id)
    if not step:
        raise HTTPException(status_code=409, detail="No running workflow step to interrupt")
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="workflow_interrupted",
        detail=f"Simulated worker kill on {step.department.value if step.department else step.name}",
    )
    return {"step": step, "steps": runner.get_steps(case_id)}
