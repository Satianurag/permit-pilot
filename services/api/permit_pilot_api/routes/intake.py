from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from permit_pilot_core.fleet_runner import init_department_steps
from permit_pilot_core.models import CreateCaseRequest, IntakeRequest
from permit_pilot_core.parcel import resolve_parcel
from permit_pilot_core.platform.armor import sanitize_user_prompt
from permit_pilot_core.platform.tasks import enqueue_distribution
from permit_pilot_core.security.pii import redact_pii
from permit_pilot_core.socrata.client import SocrataClient
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/cases", tags=["intake"], dependencies=[Depends(get_current_user)])


class PacketPreviewRequest(BaseModel):
    packet_text: str


@router.post("/intake/preview-redaction")
def preview_packet_redaction(body: PacketPreviewRequest):
    redacted, findings = redact_pii(body.packet_text)
    armor = sanitize_user_prompt(body.packet_text)
    if armor.blocked:
        findings = list(findings) + ["Model Armor blocked prompt-injection content"]
    return {"redacted_text": redacted, "findings": findings, "armor": armor}


@router.post("/intake")
async def intake_case(
    payload: IntakeRequest,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    socrata = SocrataClient()

    if payload.work_type:
        armor = sanitize_user_prompt(payload.work_type)
        if armor.blocked:
            raise HTTPException(status_code=400, detail="Model Armor blocked the work-type field")

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
    resolved = await resolve_parcel(create_payload, socrata)
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

    store.save_workflow_steps(case.id, init_department_steps())
    try:
        task_name = enqueue_distribution(case_id=case.id, reason="intake")
        store.append_audit(case.id, actor="system", action="fleet_enqueued", detail=task_name)
    except Exception as exc:
        store.append_audit(
            case.id,
            actor="system",
            action="fleet_enqueue_failed",
            detail=str(exc),
        )
        raise HTTPException(status_code=503, detail="Cloud Tasks enqueue failed") from exc

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
