from typing import Annotated, Any
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from permit_pilot_core.fleet_runner import run_distribution
from permit_pilot_core.platform.tasks import (
    case_id_from_eventarc_payload,
    case_id_from_firestore_name,
    claim_status_from_eventarc_payload,
    enqueue_distribution,
    public_base_url,
)
from permit_pilot_core.settings import get_settings
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


def _verify_oidc(authorization: str | None, *, allowed: set[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing OIDC bearer token")
    token = authorization.split(" ", 1)[1]
    audiences = {public_base_url()}
    settings = get_settings()
    if settings.permit_pilot_url:
        audiences.add(settings.permit_pilot_url.rstrip("/"))
    audiences.add(f"{public_base_url()}/api/internal/eventarc/claims")
    last_error: Exception | None = None
    info = None
    for audience in audiences:
        try:
            info = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), audience=audience
            )
            break
        except Exception as exc:
            last_error = exc
    if info is None:
        raise HTTPException(status_code=401, detail=f"Invalid OIDC token: {last_error}") from last_error
    email = str(info.get("email") or "")
    if email not in allowed:
        raise HTTPException(status_code=403, detail="Unexpected task identity")
    return email


def _tasks_sa() -> str:
    settings = get_settings()
    return (
        settings.cloud_tasks_service_account
        or f"permit-pilot-tasks@{settings.project_id}.iam.gserviceaccount.com"
    )


def _eventarc_sa() -> str:
    settings = get_settings()
    return f"permit-pilot-api@{settings.project_id}.iam.gserviceaccount.com"


@router.post("/distribution/run")
async def run_distribution_task(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    actor = _verify_oidc(authorization, allowed={_tasks_sa()})
    body = await request.json()
    case_id = str(body.get("case_id") or "")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    store = store_from_request(request)
    engine = engine_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    reviews = await run_distribution(
        store,
        engine,
        case_id=case_id,
        user_id=actor,
        reason=str(body.get("reason") or "intake"),
    )
    store.append_audit(
        case_id,
        actor=actor,
        action="cloud_task_distribution",
        detail=f"{len(reviews)} department reviews",
    )
    return {"case_id": case_id, "departments": len(reviews)}


@router.post("/eventarc/claims")
async def eventarc_claim_written(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """Firestore claim updates (including weeks-later applicant replies) enqueue a Cloud Task."""
    actor = _verify_oidc(authorization, allowed={_eventarc_sa()})
    case_id = _case_id_from_request(request)
    if not case_id:
        body = await _event_body(request)
        case_id = case_id_from_eventarc_payload(body)
        status = claim_status_from_eventarc_payload(body)
        if status and status != "resolved":
            return {"ignored": True, "case_id": case_id, "status": status}
    if not case_id:
        raise HTTPException(status_code=400, detail="Could not parse case_id from Firestore event")
    store = store_from_request(request)
    if not store.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    task_name = enqueue_distribution(case_id=case_id, reason="eventarc_claim_resume")
    store.append_audit(
        case_id,
        actor=actor,
        action="eventarc_claim_resume_enqueued",
        detail=task_name,
    )
    try:
        case = store.get_case(case_id)
        if case:
            from permit_pilot_core.platform import memory as memory_bank

            memory_bank.create_fact(
                bbl=case.bbl,
                fact=f"Applicant responded on {case.address}. Re-check open objections for this property.",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Property note (Memory Bank) write failed for Eventarc resume on %s: %s", case_id, exc)
    return {"queued": True, "task": task_name, "case_id": case_id}


def _case_id_from_request(request: Request) -> str | None:
    for header in ("ce-document", "ce-subject", "Ce-Document", "Ce-Subject"):
        raw = request.headers.get(header) or ""
        if not raw:
            continue
        found = case_id_from_firestore_name(raw)
        if found:
            return found
        if "cases/" in raw:
            found = case_id_from_firestore_name("documents/" + raw.split("documents/", 1)[-1])
            if found:
                return found
            parts = raw.split("cases/", 1)[-1].split("/")
            if parts and parts[0]:
                return parts[0]
    return None


async def _event_body(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "protobuf" in content_type or "octet-stream" in content_type:
        return {}
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
