from __future__ import annotations

from pydantic import BaseModel, Field


class FleetAgent(BaseModel):
    name: str
    description: str
    instruction: str
    tools: list[str] = Field(default_factory=list)
    department: str | None = None


PERSIST_TOOL = "persist_review"
VALIDATE_TOOL = "validate_citations"

FLEET: list[FleetAgent] = [
    FleetAgent(
        name="zoning_agent",
        department="zoning",
        description="NYC zoning review using live DCP PLUTO records.",
        instruction=(
            "You are the NYC zoning department agent. Use lookup_pluto for the case BBL. "
            "Summarize zoning district, land use, and historic district fields. "
            "Call persist_review with department=zoning, a PASS/FAIL/NEEDS_INFO status, "
            "summary, findings, and evidence drawn only from tool results."
        ),
        tools=["lookup_pluto", PERSIST_TOOL],
    ),
    FleetAgent(
        name="building_agent",
        department="building",
        description="DOB permit and violation review from NYC Open Data.",
        instruction=(
            "You are the NYC DOB building agent. Use lookup_dob_permits and lookup_dob_violations. "
            "FAIL when active DOB violations exist and cite 1 RCNY 101-07. "
            "Call persist_review with department=building using only tool evidence."
        ),
        tools=["lookup_dob_permits", "lookup_dob_violations", PERSIST_TOOL],
    ),
    FleetAgent(
        name="fire_agent",
        department="fire",
        description="FDNY violation review from NYC Open Data.",
        instruction=(
            "You are the FDNY review agent. Use lookup_fdny_violations for the BIN. "
            "FAIL open violations and cite FC 901.7. Call persist_review with department=fire."
        ),
        tools=["lookup_fdny_violations", PERSIST_TOOL],
    ),
    FleetAgent(
        name="utilities_agent",
        department="utilities",
        description="DEP ECB violation review from NYC Open Data.",
        instruction=(
            "You are the DEP utilities agent. Use lookup_dep_ecb. "
            "FAIL open DEP ECB records and cite DEP Rules. Call persist_review with department=utilities."
        ),
        tools=["lookup_dep_ecb", PERSIST_TOOL],
    ),
    FleetAgent(
        name="landmarks_agent",
        department="landmarks",
        description="Landmarks Preservation Commission review from NYC Open Data.",
        instruction=(
            "You are the LPC agent. Use lookup_landmarks. "
            "Demolition in landmark context is FAIL citing NYC LPC. Call persist_review with department=landmarks."
        ),
        tools=["lookup_landmarks", PERSIST_TOOL],
    ),
    FleetAgent(
        name="housing_agent",
        department="housing",
        description="HPD violation review from NYC Open Data.",
        instruction=(
            "You are the HPD housing agent. Use lookup_hpd_violations. "
            "FAIL open Class A violations citing HMC §27-2115. Call persist_review with department=housing."
        ),
        tools=["lookup_hpd_violations", PERSIST_TOOL],
    ),
    FleetAgent(
        name="critic_agent",
        department="critic",
        description="Cite-or-reject validator grounded in the ordinance index.",
        instruction=(
            "You are the compliance critic. Call validate_citations for the case. "
            "Do not invent ordinance codes. Persist the critic verdict with persist_review department=critic."
        ),
        tools=[VALIDATE_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="permit_orchestrator",
        department=None,
        description="NYC permit review orchestrator coordinating department agents.",
        instruction=(
            "Coordinate a full NYC building-permit distribution. "
            "Delegate to zoning, building, fire, utilities, landmarks, and housing agents, "
            "then the critic. Use parcel memory for the BBL when available. "
            "After department tools run, persist each review. "
            "Finish with a 3-sentence clerk briefing that cites only tool evidence."
        ),
        tools=[
            "lookup_pluto",
            "lookup_dob_permits",
            "lookup_dob_violations",
            "lookup_fdny_violations",
            "lookup_hpd_violations",
            "lookup_dep_ecb",
            "lookup_landmarks",
            VALIDATE_TOOL,
            PERSIST_TOOL,
        ],
    ),
]


def fleet_by_name() -> dict[str, FleetAgent]:
    return {agent.name: agent for agent in FLEET}


def department_agents() -> list[FleetAgent]:
    return [agent for agent in FLEET if agent.department and agent.department != "critic"]
