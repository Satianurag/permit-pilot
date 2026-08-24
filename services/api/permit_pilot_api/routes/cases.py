from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Case, CaseDecision, CaseStatus, Claim, CreateCaseRequest
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/cases", tags=["cases"])


class ClaimRequest(BaseModel):
    message: str


@router.get("")
def list_cases(request: Request) -> list[Case]:
    store = store_from_request(request)
    return store.list_cases()


@router.get("/{case_id}")
def get_case(case_id: str, request: Request) -> Case:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("")
async def create_case(payload: CreateCaseRequest, request: Request) -> Case:
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.create_case(payload)
    runner = WorkflowRunner(store, engine)
    await runner.run_all(case.id, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    store.create_task(
        case.id,
        title=f"Review distribution — BIN {case.bin or case.bbl}",
        task_type="distribution_review",
    )
    store.append_audit(
        case.id,
        actor="clerk",
        action="case_created",
        detail=f"Intake for {case.address}",
    )
    return case


@router.get("/{case_id}/distribution")
def get_distribution(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_distribution(case_id)


@router.post("/{case_id}/distribution/refresh")
async def refresh_distribution(case_id: str, request: Request):
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    reviews = await engine.run_all(bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    store.save_distribution(case_id, reviews)
    store.append_audit(case_id, actor="system", action="distribution_refreshed", detail="Live NYC Open Data pull")
    return reviews


@router.get("/{case_id}/tasks")
def get_case_tasks(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_tasks(case_id)


@router.get("/{case_id}/claims")
def get_claims(case_id: str, request: Request) -> list[Claim]:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_claims(case_id)


@router.post("/{case_id}/claims")
def post_claim(case_id: str, body: ClaimRequest, request: Request) -> Claim:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    claim = store.create_claim(case_id, body.message)
    store.append_audit(case_id, actor="clerk", action="claim_opened", detail=body.message)
    return claim


@router.get("/{case_id}/audit")
def get_audit(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_audit(case_id)


@router.post("/{case_id}/decision")
def post_decision(case_id: str, body: CaseDecision, request: Request) -> Case:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if body.decision == "approve":
        store.set_case_status(case_id, CaseStatus.APPROVED)
    else:
        store.set_case_status(case_id, CaseStatus.CHANGES_REQUESTED)
    store.append_audit(case_id, actor="clerk", action=body.decision, detail=body.note)
    updated = store.get_case(case_id)
    assert updated is not None
    return updated
