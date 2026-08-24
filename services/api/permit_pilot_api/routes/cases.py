from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from permit_pilot_core.decisions import approval_block_message, failed_review_departments
from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import (
    Case,
    CaseBundle,
    CaseDecision,
    CaseStatus,
    Claim,
    ClaimResponseRequest,
    CreateCaseRequest,
    IntakeDocument,
)
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/cases", tags=["cases"], dependencies=[Depends(get_current_user)])


class ClaimRequest(BaseModel):
    message: str


@router.get("")
def list_cases(
    request: Request,
    q: Annotated[str | None, Query(description="Search address, BBL, BIN, status")] = None,
) -> list[Case]:
    store = store_from_request(request)
    return store.list_cases(query=q)


@router.get("/{case_id}")
def get_case(case_id: str, request: Request) -> Case:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/{case_id}/bundle")
def get_case_bundle(case_id: str, request: Request) -> CaseBundle:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseBundle(
        case=case,
        distribution=store.list_distribution(case_id),
        claims=store.list_claims(case_id),
        audit=store.list_audit(case_id),
        workflow=store.list_workflow_steps(case_id),
        trace=store.list_trace_spans(case_id),
        observability=observability_links(case_id=case_id, project_id=gcp_project_id()),
        document=store.get_intake_document(case_id),
    )


@router.post("")
async def create_case(
    payload: CreateCaseRequest,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Case:
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
        actor=clerk_actor(current_user),
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
async def refresh_distribution(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    reviews = await engine.run_all(bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
    store.save_distribution(case_id, reviews)
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="distribution_refreshed",
        detail="Live NYC Open Data pull",
    )
    return reviews


@router.get("/{case_id}/tasks")
def get_case_tasks(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_tasks(case_id, status=None)


@router.get("/{case_id}/documents")
def get_documents(case_id: str, request: Request) -> IntakeDocument:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    document = store.get_intake_document(case_id)
    if not document:
        raise HTTPException(status_code=404, detail="No intake document on file for this case")
    return document


@router.get("/{case_id}/claims")
def get_claims(case_id: str, request: Request) -> list[Claim]:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_claims(case_id)


@router.post("/{case_id}/claims")
def post_claim(
    case_id: str,
    body: ClaimRequest,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Claim:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    claim = store.create_claim(case_id, body.message)
    store.append_audit(case_id, actor=clerk_actor(current_user), action="claim_opened", detail=body.message)
    return claim


@router.post("/{case_id}/claims/{claim_id}/respond")
def respond_to_claim(
    case_id: str,
    claim_id: str,
    body: ClaimResponseRequest,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Claim:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    claim = store.respond_to_claim(case_id, claim_id, body.message.strip())
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    store.create_task(
        case_id,
        title=f"Review applicant response — {case_id[:8]}",
        task_type="claim_response",
    )
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="claim_responded",
        detail=body.message.strip(),
    )
    return claim


@router.get("/{case_id}/audit")
def get_audit(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_audit(case_id)


@router.post("/{case_id}/decision")
def post_decision(
    case_id: str,
    body: CaseDecision,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Case:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status in {CaseStatus.APPROVED, CaseStatus.CHANGES_REQUESTED}:
        raise HTTPException(status_code=409, detail="This case already has a final clerk decision")
    if not body.note.strip():
        raise HTTPException(status_code=400, detail="Clerk note is required for audit")
    if body.decision == "approve":
        failed = failed_review_departments(store.list_distribution(case_id))
        blocked = approval_block_message(failed, body.override)
        if blocked:
            raise HTTPException(status_code=409, detail=blocked)
        store.set_case_status(case_id, CaseStatus.APPROVED)
    else:
        store.set_case_status(case_id, CaseStatus.CHANGES_REQUESTED)
    store.complete_open_tasks_for_case(case_id)
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action=body.decision,
        detail=body.note.strip(),
    )
    updated = store.get_case(case_id)
    assert updated is not None
    return updated
