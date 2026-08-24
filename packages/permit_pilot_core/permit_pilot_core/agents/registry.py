from __future__ import annotations

from pydantic import BaseModel, Field

from permit_pilot_core.security.agent_gateway import agent_fingerprint, trusted_agent_fingerprints


class AgentCard(BaseModel):
    name: str
    description: str
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    signed: bool = False
    fingerprint: str = ""


_REGISTERED: list[AgentCard] = [
    AgentCard(
        name="zoning_agent",
        description="NYC zoning review using live DCP PLUTO records.",
        skills=["zoning", "land-use"],
        tools=["lookup_pluto"],
    ),
    AgentCard(
        name="building_agent",
        description="DOB permit and violation review from NYC Open Data.",
        skills=["building", "permits", "violations"],
        tools=["lookup_permits"],
    ),
    AgentCard(
        name="distribution_agent",
        description="Cross-department distribution orchestration against live Open Data.",
        skills=["orchestration", "distribution"],
        tools=["run_distribution_review"],
    ),
    AgentCard(
        name="critic_agent",
        description="Cite-or-reject validator — fails reviews without ordinance citations.",
        skills=["compliance", "citations"],
        tools=["validate_citations"],
    ),
]


def list_agent_cards() -> list[AgentCard]:
    trusted = trusted_agent_fingerprints()
    cards: list[AgentCard] = []
    for card in _REGISTERED:
        fp = agent_fingerprint(card.name)
        cards.append(
            card.model_copy(
                update={
                    "fingerprint": fp,
                    "signed": fp in trusted,
                }
            )
        )
    return cards
