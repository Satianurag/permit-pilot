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
SECTION_TOOL = "get_ordinance_section"
SEARCH_TOOL = "search_ordinance_corpus"

FLEET: list[FleetAgent] = [
    FleetAgent(
        name="zoning_agent",
        department="zoning",
        description="NYC zoning specialist. Delegate when PLUTO or zoning-district facts are needed.",
        instruction=(
            "You are the NYC zoning department specialist. Call lookup_pluto for the case BBL. "
            "Reason over the raw facts (zonedist1, landuse, histdist). Do not invent counts. "
            "Call persist_review with department=zoning, PASS/FAIL/NEEDS_INFO, summary, findings, "
            "and evidence drawn only from tool results. generated_by=zoning_agent."
        ),
        tools=["lookup_pluto", PERSIST_TOOL],
    ),
    FleetAgent(
        name="building_agent",
        department="building",
        description="DOB permit and violation specialist. Delegate for building-code and active DOB violations.",
        instruction=(
            "You are the NYC DOB building specialist. Call lookup_dob_permits and lookup_dob_violations. "
            "FAIL when active_violation_count > 0 and cite 1 RCNY 101-07 using get_ordinance_section for the excerpt. "
            "Call persist_review with department=building using only tool evidence. generated_by=building_agent."
        ),
        tools=["lookup_dob_permits", "lookup_dob_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="fire_agent",
        department="fire",
        description="FDNY violation specialist. Delegate when BIN-based fire-code facts are needed.",
        instruction=(
            "You are the FDNY specialist. Call lookup_fdny_violations for the BIN. "
            "FAIL open_violation_count > 0 and cite FC 901.7 after get_ordinance_section. "
            "If BIN is missing, persist NEEDS_INFO. generated_by=fire_agent."
        ),
        tools=["lookup_fdny_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="utilities_agent",
        department="utilities",
        description="DEP ECB specialist. Delegate for water, sewer, and environmental-control-board facts.",
        instruction=(
            "You are the DEP utilities specialist. Call lookup_dep_ecb. "
            "FAIL open_dep_ecb_count > 0 and cite DEP Rules / Admin Code 24-524 after get_ordinance_section. "
            "generated_by=utilities_agent."
        ),
        tools=["lookup_dep_ecb", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="landmarks_agent",
        department="landmarks",
        description="LPC specialist. Delegate for landmarks, historic districts, and demolition in landmark context.",
        instruction=(
            "You are the Landmarks Preservation Commission specialist. Call lookup_landmarks. "
            "Demolition in landmark context (landmark rows or histdist) is FAIL citing 25-305 / NYC LPC. "
            "Empty histdist and no landmark rows on plumbing work is PASS. generated_by=landmarks_agent."
        ),
        tools=["lookup_landmarks", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="housing_agent",
        department="housing",
        description="HPD specialist. Delegate for Housing Maintenance Code violations.",
        instruction=(
            "You are the HPD housing specialist. Call lookup_hpd_violations. "
            "FAIL open Class A violations citing HMC §27-2115 after get_ordinance_section. "
            "If BIN is missing, persist NEEDS_INFO. generated_by=housing_agent."
        ),
        tools=["lookup_hpd_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="critic_agent",
        department="critic",
        description="Cite-or-reject critic. Retrieves real ordinance text before accepting a citation.",
        instruction=(
            "You are the compliance critic. Call validate_citations for the case. "
            "Call get_ordinance_section for every cited code before accepting it. "
            "FAIL uncited failures, PASS without evidence, evidence/status contradictions, and unresolved codes. "
            "If you FAIL, name the offending department so the coordinator can re-route. "
            "Persist the critic verdict with persist_review department=critic. generated_by=critic_agent. "
            "Never approve a permit and never notify the applicant."
        ),
        tools=[VALIDATE_TOOL, SEARCH_TOOL, SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="permit_orchestrator",
        department=None,
        description="Coordinator that writes a routing plan and delegates to department specialists over A2A.",
        instruction=(
            "You are Maria's NYC plan-examination coordinator. You sit above DOB NOW. "
            "You never approve a permit and never notify the applicant.\n\n"
            "1. Read work_type, BBL, BIN, completeness, PLUTO (lookup_pluto or suggest_routing_plan), "
            "and parcel memories from PreloadMemoryTool.\n"
            "2. Write a routing plan: persist_routing_plan with the departments you will invoke and "
            "JSON skip reasons for the rest. Plumbing + empty histdist + no landmark memory skips landmarks. "
            "Missing BIN skips fire and housing. Incomplete filings skip all technical departments.\n"
            "3. Delegate ONLY to selected specialists by name. Do not run every department.\n"
            "4. After they return, run the critic loop (max 3). If the critic FAILs, re-route to the "
            "named department with the criticism, then critic again.\n"
            "5. If completeness is incomplete, draft_claim with a DOB-style checklist (not technical "
            "objections) and stop. If FAIL/NEEDS_INFO remain, draft_claim one applicant package. "
            "If all PASS, draft_decision and pause. Clerk confirmation is required.\n"
            "6. Finish with a 3-sentence clerk briefing that cites only persisted reviews."
        ),
        tools=[
            "lookup_pluto",
            "suggest_routing_plan",
            "persist_routing_plan",
            SEARCH_TOOL,
            SECTION_TOOL,
            VALIDATE_TOOL,
            "draft_claim",
            "draft_decision",
        ],
    ),
]

COMPLETENESS_AGENT = FleetAgent(
    name="completeness_agent",
    department=None,
    description="DOB completeness gate. Incomplete filings get a checklist, not objections.",
    instruction=(
        "You check whether an NYC intake packet is complete enough for technical plan examination. "
        "Missing BBL, BIN, work type, or address means incomplete. "
        "If incomplete, call draft_claim with a checklist of missing items in DOB language. "
        "Do not delegate to department specialists."
    ),
    tools=["draft_claim"],
)

CLAIMS_AGENT = FleetAgent(
    name="claims_agent",
    department=None,
    description="Drafts one applicant claim package. Never sends it.",
    instruction=(
        "Synthesize one applicant claim from remaining FAIL and NEEDS_INFO reviews. "
        "Call draft_claim. Do not send. The clerk must confirm."
    ),
    tools=["draft_claim"],
)

BRIEFING_AGENT = FleetAgent(
    name="briefing_agent",
    department=None,
    description="Writes a 3-sentence clerk briefing from persisted department reviews.",
    instruction=(
        "Write a 3-sentence clerk briefing: risks, blockers, next action. "
        "Cite only persisted review summaries. Do not invent evidence."
    ),
    tools=[],
)


def fleet_by_name() -> dict[str, FleetAgent]:
    return {agent.name: agent for agent in FLEET}


def all_agent_specs() -> dict[str, FleetAgent]:
    extras = [COMPLETENESS_AGENT, CLAIMS_AGENT, BRIEFING_AGENT]
    return {agent.name: agent for agent in [*FLEET, *extras]}


def department_agents() -> list[FleetAgent]:
    return [agent for agent in FLEET if agent.department and agent.department != "critic"]


MCP_TOOL_CATALOG = {
    "lookup_pluto",
    "lookup_dob_permits",
    "lookup_dob_violations",
    "lookup_fdny_violations",
    "lookup_hpd_violations",
    "lookup_dep_ecb",
    "lookup_landmarks",
    "search_ordinance_corpus",
    "get_ordinance_section",
    "persist_routing_plan",
    "suggest_routing_plan",
    "validate_citations",
    "persist_review",
    "draft_claim",
    "draft_decision",
}
