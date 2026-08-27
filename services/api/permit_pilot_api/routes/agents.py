from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from permit_pilot_core.platform import memory as memory_bank
from permit_pilot_core.platform import registry
from permit_pilot_core.platform.armor import sanitize_user_prompt
from permit_pilot_core.platform.fleet import FLEET
from permit_pilot_core.platform.identity import agent_iap_principal, agent_spiffe
from permit_pilot_core.settings import get_settings
from permit_pilot_api.auth import ClerkUser, get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links

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
