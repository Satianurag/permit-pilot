from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.platform import memory as memory_bank
from permit_pilot_core.platform import registry
from permit_pilot_core.platform.armor import sanitize_user_prompt
from permit_pilot_core.platform.fleet import FLEET, fleet_by_name
from permit_pilot_core.platform.gateway import fingerprint_allowed, signed_fingerprint
from permit_pilot_core.platform.identity import agent_iap_principal, agent_spiffe
from permit_pilot_core.platform import runtime
from permit_pilot_core.settings import get_settings
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links
from permit_pilot_api.deps import store_from_request

router = APIRouter(tags=["agents"], dependencies=[Depends(get_current_user)])


@router.get("/agents")
def get_agents():
    live = registry.catalog()
    settings = get_settings()
    cards = []
    for spec in FLEET:
        engine_id = settings.engine_id_map.get(spec.name, "")
        cards.append(
            {
                "name": spec.name,
                "description": spec.description,
                "skills": [spec.department] if spec.department else ["orchestration"],
                "tools": spec.tools,
                "engine_id": engine_id,
                "identity_type": "AGENT_IDENTITY",
                "signed": bool(engine_id),
                "fingerprint": signed_fingerprint(spec.name),
                "spiffe": agent_spiffe(engine_id) if engine_id else "",
                "iap_principal": agent_iap_principal(engine_id) if engine_id else "",
            }
        )
    return {"agents": cards, "registry": live}


@router.get("/governance")
def get_governance():
    settings = get_settings()
    live = registry.catalog()
    links = observability_links(case_id=None, project_id=gcp_project_id())
    return {
        "gateway": settings.agent_gateway_name,
        "gateway_resource": (
            f"projects/{settings.project_id}/locations/{settings.region}/"
            f"agentGateways/{settings.agent_gateway_name}"
        ),
        "model_armor_template": settings.model_armor_template,
        "vertex_model": settings.vertex_model,
        "vertex_location": settings.vertex_location,
        "mcp_tools_url": settings.mcp_tools_url,
        "registry": live,
        "engines": settings.engine_id_map,
        "console": links,
    }


@router.get("/memory/{bbl}")
def get_parcel_memory(bbl: str, q: str | None = None):
    try:
        memories = memory_bank.retrieve(bbl=bbl, query=q)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Memory Bank unavailable: {exc}") from exc
    return {"bbl": bbl, "memories": memories}


@router.post("/armor/inspect")
async def inspect_text(request: Request, _user: Annotated[ClerkUser, Depends(get_current_user)]):
    body = await request.json()
    text = str(body.get("text") or "")
    verdict = sanitize_user_prompt(text)
    return verdict


@router.post("/agents/{name}/invoke")
async def invoke_agent(
    name: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    """Clerk invoke through the Agent Gateway fingerprint allowlist. Tampered fingerprints 403."""
    if name not in fleet_by_name():
        raise HTTPException(status_code=404, detail="Unknown agent")
    body = await request.json()
    fingerprint = str(body.get("fingerprint") or "")
    message = str(body.get("message") or "Gateway ping from clerk UI.")
    case_id = str(body.get("case_id") or "")
    store = store_from_request(request)
    actor = clerk_actor(current_user)
    if not fingerprint_allowed(name, fingerprint):
        detail = (
            "Agent Gateway fingerprint allowlist rejected this invoke. "
            "The request was unsigned or tampered."
        )
        if case_id and store.get_case(case_id):
            store.append_audit(case_id, actor=actor, action="gateway_invoke_denied", detail=f"{name}: {detail}")
        raise HTTPException(status_code=403, detail=detail)
    settings = get_settings()
    engine_id = settings.engine_id_map.get(name, "")
    if not engine_id:
        raise HTTPException(status_code=503, detail=f"{name} is not deployed on Agent Runtime")
    inbound = sanitize_user_prompt(message)
    if inbound.blocked:
        raise HTTPException(status_code=403, detail="Model Armor blocked the invoke prompt")
    try:
        events = runtime.stream_query(engine_id=engine_id, user_id=current_user.username, message=message)
        text = runtime.extract_text(events)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent Runtime invoke failed: {exc}") from exc
    if case_id and store.get_case(case_id):
        store.append_audit(
            case_id,
            actor=actor,
            action="gateway_invoke_ok",
            detail=f"{name}: {(text or 'ok')[:300]}",
        )
    return {
        "ok": True,
        "agent": name,
        "engine_id": engine_id,
        "text": text,
        "fingerprint": "allowlist",
    }
