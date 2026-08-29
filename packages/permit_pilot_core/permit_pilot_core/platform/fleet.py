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

OBJECTION_RULES = (
    "Existing Open Data rows are parcel context, not automatic FAIL. "
    "Read description, type, and status. An unrelated elevator or certificate issue is not an objection "
    "on a plumbing kitchen job; demolition with open structural or landmark facts may be. "
    "Draft numbered objections only when the row is relevant to this work type: "
    "objections_json as [{obj_no, department, code, description, recommended_fix, status}]. "
    "Call get_ordinance_section for every code before persist_review. "
    "PASS with an empty objections list when nothing warrants a technical objection. "
    "NEVER FAIL solely because a count field is greater than zero. "
    "Never approve a permit and never notify the applicant."
)

FLEET: list[FleetAgent] = [
    FleetAgent(
        name="zoning_agent",
        department="zoning",
        description="NYC zoning specialist. Delegate when PLUTO or zoning-district facts are needed.",
        instruction=(
            "You are the NYC zoning specialist for a plan examiner. Call lookup_pluto for the case BBL. "
            "Reason over zonedist1, landuse, and histdist. Do not invent counts. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=zoning. generated_by=zoning_agent."
        ),
        tools=["lookup_pluto", PERSIST_TOOL],
    ),
    FleetAgent(
        name="building_agent",
        department="building",
        description="DOB permit and violation specialist. Delegate for building-code and active DOB violations.",
        instruction=(
            "You are the NYC DOB building specialist for a plan examiner. "
            "Call lookup_dob_permits and lookup_dob_violations. "
            "Read each violation description — do not treat active_violation_count as a verdict. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=building. generated_by=building_agent."
        ),
        tools=["lookup_dob_permits", "lookup_dob_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="fire_agent",
        department="fire",
        description="FDNY violation specialist. Delegate when BIN-based fire-code facts are needed.",
        instruction=(
            "You are the FDNY specialist for a plan examiner. Call lookup_fdny_violations for the BIN. "
            "The FDNY dataset is historical (frozen around 2017) — treat it as context, not current open orders. "
            "If BIN is missing, persist NEEDS_INFO. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=fire. generated_by=fire_agent."
        ),
        tools=["lookup_fdny_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="utilities_agent",
        department="utilities",
        description="DEP ECB specialist. Delegate for water, sewer, and environmental-control-board facts.",
        instruction=(
            "You are the DEP utilities specialist for a plan examiner. Call lookup_dep_ecb. "
            "Read each ECB row. Do not FAIL solely because open_dep_ecb_count is greater than zero. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=utilities. generated_by=utilities_agent."
        ),
        tools=["lookup_dep_ecb", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="landmarks_agent",
        department="landmarks",
        description="LPC specialist. Delegate for landmarks, historic districts, and demolition in landmark context.",
        instruction=(
            "You are the Landmarks Preservation Commission specialist for a plan examiner. Call lookup_landmarks. "
            "Demolition in landmark context (landmark rows or histdist) is a candidate objection citing 25-305 / NYC LPC "
            "after get_ordinance_section — not an automatic count FAIL. "
            "Empty histdist and no landmark rows on plumbing work is PASS with no objections. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=landmarks. generated_by=landmarks_agent."
        ),
        tools=["lookup_landmarks", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="housing_agent",
        department="housing",
        description="HPD specialist. Delegate for Housing Maintenance Code violations.",
        instruction=(
            "You are the HPD housing specialist for a plan examiner. Call lookup_hpd_violations with BIN and BBL. "
            "HPD is keyed by borough/block/lot, not BIN. Class C or open HMC rows may be objections when relevant "
            "to this residential work; do not FAIL solely on class counts. "
            f"{OBJECTION_RULES} "
            "Call persist_review with department=housing. generated_by=housing_agent."
        ),
        tools=["lookup_hpd_violations", SECTION_TOOL, PERSIST_TOOL],
    ),
    FleetAgent(
        name="critic_agent",
        department="critic",
        description="Cite-or-reject critic. Retrieves real ordinance text before accepting a citation.",
        instruction=(
            "You are the compliance critic. Call validate_citations for the case. "
            "Call get_ordinance_section for every cited code and every objection code before accepting it. "
            "FAIL uncited FAIL reviews, open objections without a code, PASS without evidence, "
            "PASS that still has open objections, and codes that do not resolve in the ordinance corpus. "
            "Do not treat Open Data count fields as contradictions — existing violations are parcel context. "
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
            "and parcel memories from PreloadMemoryTool. Memories are property notes for this BBL, including "
            "prior objections still open from an earlier filing.\n"
            "2. Write a routing plan: persist_routing_plan with the departments you will invoke and "
            "JSON skip reasons for the rest, in clerk language. Plumbing + empty histdist + no landmark memory "
            "skips landmarks. Missing BIN skips fire. Incomplete filings skip all technical departments.\n"
            "3. Delegate ONLY to selected specialists by name. Do not run every department.\n"
            "4. After they return, run the critic loop (max 3). If the critic FAILs, re-route to the "
            "named department with the criticism, then critic again.\n"
            "5. If completeness is incomplete, draft_claim with a DOB-style checklist (not technical "
            "objections) and stop. If open objections or FAIL/NEEDS_INFO remain, draft_claim one applicant "
            "package that lists numbered objections (Obj #, section of code, description). "
            "If all PASS with no open objections, draft_decision and pause. Clerk confirmation is required.\n"
            "6. Finish with a 3-sentence clerk briefing that cites only persisted reviews. "
            "Do not mention Agent Runtime, A2A, SPIFFE, or HITL."
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
        "Do not write technical objections and do not delegate to department specialists."
    ),
    tools=["draft_claim"],
)

CLAIMS_AGENT = FleetAgent(
    name="claims_agent",
    department=None,
    description="Drafts one applicant claim package. Never sends it.",
    instruction=(
        "Synthesize one applicant claim from remaining FAIL, NEEDS_INFO, and open objections. "
        "Use DOB first-review form: Obj #, section of code, description. Completeness items stay a checklist. "
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
        "Cite only persisted review summaries and numbered objections. Do not invent evidence. "
        "Do not mention agents, runtimes, or gateways."
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
