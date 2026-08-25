from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from permit_pilot_core.agents.registry import list_agent_cards
from permit_pilot_core.security.agent_gateway import verify_agent_signature
from permit_pilot_api.auth import ClerkUser, clerk_actor, get_current_admin, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(tags=["agents"])


@router.get("/agents")
def get_agents(_user: Annotated[ClerkUser, Depends(get_current_user)]):
    return list_agent_cards()


@router.post("/agents/{agent_name}/invoke")
def invoke_agent(
    agent_name: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_admin)],
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
                    detail=f"Unsigned or untrusted agent blocked at gateway: {agent_name}",
                )
        raise HTTPException(
            status_code=403,
            detail=f"Gateway blocked unsigned agent: {agent_name}",
        )
    return {"agent": agent_name, "status": "authorized", "message": "Agent signature verified"}
