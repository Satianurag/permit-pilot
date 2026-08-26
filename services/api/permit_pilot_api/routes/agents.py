from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from permit_pilot_core.agents.registry import list_agent_cards
from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.security.agent_gateway import agent_fingerprint, verify_agent_signature
from permit_pilot_core.socrata.client import SocrataClient
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_user
from permit_pilot_api.deps import engine_from_request, store_from_request

router = APIRouter(tags=["agents"])


async def _run_agent_action(
    agent_name: str,
    case_id: str | None,
    engine: DistributionEngine,
    store,
) -> str:
    if not case_id:
        return "Fingerprint verified — attach X-Case-Id to run live Open Data tools."
    case = store.get_case(case_id)
    if not case:
        return "Fingerprint verified — case not found for live tools."
    socrata = SocrataClient()
    if agent_name == "zoning_agent":
        rows = await socrata.pluto_by_bbl(case.bbl)
        zones = [str(row.get("zonedist1") or row.get("zonedist") or "") for row in rows[:3]]
        return f"PLUTO zoning for BBL {case.bbl}: {', '.join(zones) or 'no rows'}"
    if agent_name == "building_agent":
        rows = await socrata.permits_by_bbl(case.bbl)
        return f"DOB permits on BBL {case.bbl}: {len(rows)} recent filing rows"
    if agent_name == "distribution_agent":
        reviews = await engine.run_all(bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
        summary = ", ".join(f"{r.department.value}:{r.status.value}" for r in reviews)
        return f"Distribution orchestrator ran {len(reviews)} departments — {summary}"
    if agent_name == "critic_agent":
        reviews = store.list_distribution(case_id)
        critic = await engine.review_critic(reviews=reviews)
        return f"Critic policy check: {critic.status.value} — {critic.summary}"
    return "Fingerprint verified against allowlist."


@router.get("/agents")
def get_agents(_user: Annotated[ClerkUser, Depends(get_current_user)]):
    return list_agent_cards()


@router.post("/agents/{agent_name}/invoke")
async def invoke_agent(
    agent_name: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
    x_agent_signature: str | None = Header(default=None),
    x_case_id: str | None = Header(default=None),
):
    if not verify_agent_signature(agent_name, x_agent_signature):
        if x_case_id:
            store = store_from_request(request)
            if store.get_case(x_case_id):
                store.append_audit(
                    x_case_id,
                    actor=clerk_actor(current_user),
                    action="agent_rejected",
                    detail=f"Fingerprint gateway blocked untrusted agent: {agent_name}",
                )
        raise HTTPException(
            status_code=403,
            detail=f"Gateway blocked agent — fingerprint not on allowlist: {agent_name}",
        )
    store = store_from_request(request)
    engine = engine_from_request(request)
    if x_case_id and store.get_case(x_case_id):
        store.append_audit(
            x_case_id,
            actor=clerk_actor(current_user),
            action="agent_authorized",
            detail=f"Fingerprint gateway admitted agent: {agent_name}",
        )
    message = await _run_agent_action(agent_name, x_case_id, engine, store)
    return {
        "agent": agent_name,
        "status": "authorized",
        "message": message,
        "fingerprint": agent_fingerprint(agent_name),
    }
