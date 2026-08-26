from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import CreateCaseRequest, IntakeRequest
from permit_pilot_core.security.pii import redact_pii
from permit_pilot_core.socrata.client import SocrataClient
from permit_pilot_core.workflow.runner import WorkflowRunner
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.config import gcp_project_id
from permit_pilot_api.deps import engine_from_request, store_from_request
from permit_pilot_api.workflow_jobs import run_distribution_background

router = APIRouter(prefix="/cases", tags=["intake"], dependencies=[Depends(get_current_user)])


class PacketPreviewRequest(BaseModel):
    packet_text: str


@router.post("/intake/preview-redaction")
def preview_packet_redaction(body: PacketPreviewRequest):
    redacted, findings = redact_pii(body.packet_text)
    return {"redacted_text": redacted, "findings": findings}


async def _resolve_bin(payload: CreateCaseRequest, socrata: SocrataClient) -> CreateCaseRequest:
    if payload.bin:
        return payload
    rows = await socrata.pluto_by_bbl(payload.bbl)
    if not rows:
        return payload
    row = rows[0]
    footprints = await socrata.building_footprints_by_bbl(payload.bbl, limit=1)
    bin_from_footprint = str(footprints[0].get("bin") or "") if footprints else ""
    return payload.model_copy(
        update={
            "bin": bin_from_footprint or str(row.get("bin") or ""),
            "address": payload.address or str(row.get("address") or ""),
            "borough": payload.borough or str(row.get("borough") or ""),
            "owner": payload.owner or str(row.get("ownername") or ""),
        }
    )


@router.post("/intake")
async def intake_case(
    payload: IntakeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store: FirestoreStore = store_from_request(request)
    engine: DistributionEngine = engine_from_request(request)
    socrata = SocrataClient()

    redacted_packet = ""
    pii_findings: list[str] = []
    if payload.packet_text.strip():
        redacted_packet, pii_findings = redact_pii(payload.packet_text)

    create_payload = CreateCaseRequest(
        address=payload.address,
        bbl=payload.bbl,
        bin=payload.bin,
        work_type=payload.work_type,
        owner=payload.owner,
        borough=payload.borough,
    )
    resolved = await _resolve_bin(create_payload, socrata)
    case = store.create_case(resolved)

    if redacted_packet:
        store.save_intake_packet(
            case.id,
            redacted_packet,
            pii_findings,
            filename=payload.packet_filename,
            content_type=payload.packet_content_type,
        )
        store.append_audit(
            case.id,
            actor="system",
            action="pii_redacted",
            detail=f"Intake packet redacted: {', '.join(pii_findings) or 'no PII detected'}",
        )

    if payload.plan_pdf_base64 and payload.plan_filename:
        store.save_intake_pdf(
            case.id,
            filename=payload.plan_filename,
            content_type=payload.plan_content_type or "application/pdf",
            pdf_base64=payload.plan_pdf_base64,
        )
        store.append_audit(
            case.id,
            actor=clerk_actor(current_user),
            action="plan_uploaded",
            detail=f"Plan PDF stored: {payload.plan_filename}",
        )

    runner = WorkflowRunner(store, engine)
    runner.init_steps(case.id)
    background_tasks.add_task(
        run_distribution_background,
        case_id=case.id,
        bbl=case.bbl,
        bin_=case.bin,
        work_type=case.work_type,
        project_id=gcp_project_id(),
    )
    store.create_task(
        case.id,
        title=f"Review distribution — BIN {case.bin or case.bbl}",
        task_type="distribution_review",
        assignee=current_user.username,
    )
    store.append_audit(
        case.id,
        actor=clerk_actor(current_user),
        action="case_intake",
        detail=f"Intake for {case.address}",
    )
    return case
