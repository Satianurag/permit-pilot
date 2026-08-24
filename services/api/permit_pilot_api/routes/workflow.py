import os

from fastapi import APIRouter, HTTPException, Request

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.orchestration.gcp_workflows import gcp_workflows_enabled, start_distribution_workflow
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/cases", tags=["workflow"])


@router.get("/{case_id}/workflow")
def get_workflow(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store)
    return runner.get_steps(case_id)


@router.post("/{case_id}/workflow/run")
async def run_workflow(case_id: str, request: Request):
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store, engine)
    steps = await runner.run_all(case.id, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    return steps


@router.post("/{case_id}/workflow/resume")
async def resume_workflow(case_id: str, request: Request):
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store, engine)
    step = await runner.run_next(case.id, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    store.append_audit(case_id, actor="system", action="workflow_resumed", detail="Distribution workflow resumed")
    return {"step": step, "steps": runner.get_steps(case_id)}


@router.post("/{case_id}/workflow/simulate-crash")
def simulate_crash(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    runner = WorkflowRunner(store)
    step = runner.simulate_crash(case_id)
    if not step:
        raise HTTPException(status_code=409, detail="No running workflow step to interrupt")
    return step


@router.post("/{case_id}/workflow/gcp-run")
def run_gcp_workflow(case_id: str, request: Request):
    """Start managed GCP Cloud Workflows execution (durable orchestration)."""
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not gcp_workflows_enabled():
        raise HTTPException(status_code=503, detail="GCP_WORKFLOW_NAME not configured")
    api_base = os.environ.get("PERMIT_PILOT_URL", "https://permit-pilot-538666547847.us-central1.run.app")
    runner = WorkflowRunner(store)
    runner.init_steps(case_id)
    execution_id = start_distribution_workflow(case_id=case_id, api_base=api_base)
    store.append_audit(
        case_id,
        actor="gcp_workflows",
        action="workflow_started",
        detail=f"Cloud Workflows execution {execution_id}",
    )
    return {"execution_id": execution_id, "engine": "gcp_workflows"}
