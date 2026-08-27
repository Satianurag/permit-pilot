from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from permit_pilot_core.decisions import (
    approval_block_message,
    checking_departments,
    failed_review_departments,
    needs_info_departments,
)
from permit_pilot_core.models import (
    Case,
    CaseBundle,
    CaseDecision,
    CaseStatus,
    Claim,
    ClaimResponseRequest,
    ClerkBriefing,
    CaseUpdateRequest,
    ParcelContext,
    RelatedPermit,
)
from permit_pilot_core.platform import memory as memory_bank
from permit_pilot_core.platform.tasks import enqueue_distribution
from permit_pilot_core.settings import get_settings
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/cases", tags=["cases"], dependencies=[Depends(get_current_user)])


class ClaimRequest(BaseModel):
    message: str


def _related_permit(row: dict) -> RelatedPermit:
    job = (
        row.get("job_filing_number")
        or row.get("job__")
        or row.get("job_number")
        or row.get("permit_si_no")
        or row.get("tracking_number")
    )
    filing = row.get("filing_date") or row.get("issuance_date") or row.get("permit_issuance_date")
    return RelatedPermit(
        job_number=str(job or "") or None,
        work_type=str(
            row.get("work_type") or row.get("job_type") or row.get("job_description") or ""
        ) or None,
        status=str(row.get("permit_status") or row.get("filing_status") or row.get("job_status") or "")
        or None,
        filing_date=str(filing or "") or None,
    )


def _briefing_from_store(raw: dict | None) -> ClerkBriefing | None:
    if not raw:
        return None
    from datetime import datetime

    return ClerkBriefing(
        summary=str(raw.get("summary") or ""),
        model=str(raw.get("model") or get_settings().vertex_model),
        generated_at=datetime.fromisoformat(str(raw["generated_at"])),
        generated_by=str(raw.get("generated_by") or "system"),
    )


def _queue_distribution(*, store, case_id: str, actor: str, reason: str, action: str) -> dict[str, str | bool]:
    try:
        task_name = enqueue_distribution(case_id=case_id, reason=reason)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Cloud Tasks enqueue failed") from exc
    store.append_audit(case_id, actor=actor, action=action, detail=task_name)
    return {"queued": True, "task": task_name, "reason": reason}


@router.get("")
def list_cases(
    request: Request,
    q: Annotated[str | None, Query(description="Search address, BBL, BIN, owner")] = None,
    status: Annotated[str | None, Query(description="Filter by case status")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max cases to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Skip cases for pagination")] = 0,
) -> list[Case]:
    store = store_from_request(request)
    return store.list_cases(query=q, status=status, limit=limit, offset=offset)


@router.get("/{case_id}")
def get_case(case_id: str, request: Request) -> Case:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}")
def patch_case(
    case_id: str,
    body: CaseUpdateRequest,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Case:
    store = store_from_request(request)
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Case not found")
    if existing.status in {CaseStatus.APPROVED, CaseStatus.CHANGES_REQUESTED}:
        raise HTTPException(status_code=409, detail="Terminal cases cannot be edited without reopening")
    fields = body.model_dump(exclude_unset=True)
    updated = store.update_case(case_id, fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Case not found")
    changes = ", ".join(f"{k}={fields[k]}" for k in fields if fields[k] is not None)
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="case_updated",
        detail=f"Case details updated: {changes}",
    )
    return updated


@router.get("/{case_id}/bundle")
def get_case_bundle(case_id: str, request: Request) -> CaseBundle:
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    memories: list = []
    try:
        memories = memory_bank.retrieve(bbl=case.bbl, query=case.work_type)
    except Exception:
        memories = []
    return CaseBundle(
        case=case,
        distribution=store.list_distribution(case_id),
        claims=store.list_claims(case_id),
        audit=store.list_audit(case_id),
        workflow=store.list_workflow_steps(case_id),
        trace=store.list_trace_spans(case_id),
        observability=observability_links(case_id=case_id, project_id=gcp_project_id()),
        document=store.get_intake_document(case_id),
        related_permits=[],
        parcel=None,
        briefing=_briefing_from_store(store.get_briefing(case_id)),
        memories=memories,
    )


@router.get("/{case_id}/trace")
def get_case_trace(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return store.list_trace_spans(case_id)


@router.get("/{case_id}/context")
async def get_case_context(case_id: str, request: Request):
    store = store_from_request(request)
    engine = engine_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    cached = store.get_context_cache(case_id)
    if cached is not None:
        parcel = cached.get("parcel")
        return {
            "related_permits": cached.get("related_permits") or [],
            "parcel": ParcelContext(**parcel) if parcel else None,
            "cached": True,
        }
    related_raw = await engine.related_permits(bbl=case.bbl, bin_=case.bin)
    parcel_raw = await engine.parcel_context(bbl=case.bbl)
    related_models = [_related_permit(row) for row in related_raw]
    parcel = ParcelContext(**parcel_raw) if parcel_raw else None
    store.save_context_cache(
        case_id,
        related_permits=[p.model_dump(mode="json") for p in related_models],
        parcel=parcel.model_dump(mode="json") if parcel else None,
    )
    return {
        "related_permits": related_models,
        "parcel": parcel,
        "cached": False,
    }


@router.get("/{case_id}/documents/pdf")
def get_plan_pdf(case_id: str, request: Request):
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    pdf = store.get_intake_pdf(case_id)
    if not pdf:
        raise HTTPException(status_code=404, detail="No plan PDF on file for this case")
    return pdf


@router.post("/{case_id}/distribution/refresh")
async def refresh_distribution(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _queue_distribution(
        store=store,
        case_id=case_id,
        actor=clerk_actor(current_user),
        reason="refresh",
        action="distribution_enqueued",
    )


@router.post("/{case_id}/distribution/refresh-bin-departments")
async def refresh_bin_departments(
    case_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.bin:
        raise HTTPException(status_code=400, detail="BIN is required before refreshing BIN-dependent reviews")
    return _queue_distribution(
        store=store,
        case_id=case_id,
        actor=clerk_actor(current_user),
        reason="bin_refresh",
        action="bin_departments_enqueued",
    )


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
    claim = store.create_claim(case_id, body.message, notify=True)
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="claim_opened",
        detail=(
            f"{body.message} — reference {claim.notification_reference} recorded for manual DOB NOW entry"
            if claim.notification_reference
            else body.message
        ),
    )
    return claim


@router.post("/{case_id}/claims/{claim_id}/mark-dob-now-sent")
def mark_claim_dob_now_sent(
    case_id: str,
    claim_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
) -> Claim:
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    claim = store.mark_claim_dob_now_sent(case_id, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="dob_now_marked_sent",
        detail=f"Clerk marked DOB NOW reference {claim.notification_reference} as sent manually",
    )
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
    case = store.get_case(case_id)
    address = case.address if case else case_id[:8]
    store.create_task(
        case_id,
        title=f"Review applicant response — {address}",
        task_type="claim_response",
        assignee=current_user.username,
    )
    store.append_audit(
        case_id,
        actor=clerk_actor(current_user),
        action="claim_responded",
        detail=body.message.strip(),
    )
    try:
        task_name = enqueue_distribution(case_id=case_id, reason="claim_response")
        store.append_audit(
            case_id,
            actor="system",
            action="fleet_enqueued",
            detail=task_name,
        )
    except Exception as exc:
        store.append_audit(
            case_id,
            actor="system",
            action="fleet_enqueue_failed",
            detail=str(exc),
        )
        raise HTTPException(status_code=503, detail="Cloud Tasks enqueue failed") from exc
    return claim


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
    if body.override and len(body.note.strip()) < get_settings().override_note_min_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Override decisions require a clerk note of at least {get_settings().override_note_min_chars} characters",
        )
    if body.decision == "approve":
        reviews = store.list_distribution(case_id)
        blocked = approval_block_message(
            failed=failed_review_departments(reviews),
            needs_info=needs_info_departments(reviews),
            checking=checking_departments(reviews),
            override=body.override,
        )
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
