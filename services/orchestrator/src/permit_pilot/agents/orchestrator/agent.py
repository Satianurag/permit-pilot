import asyncio
from typing import Any

from google.adk.agents import Agent
from google.adk.tools.function_tool import FunctionTool

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.socrata.client import SocrataClient

_engine = DistributionEngine()
_client = SocrataClient()


def _run(coro):
    return asyncio.run(coro)


def lookup_pluto(bbl: str) -> list[dict[str, Any]]:
    """Fetch DCP PLUTO zoning facts for a NYC BBL."""
    return _run(_client.pluto_by_bbl(bbl))


def lookup_permits(bbl: str) -> list[dict[str, Any]]:
    """Fetch DOB NOW permit rows for a NYC BBL."""
    return _run(_client.permits_by_bbl(bbl))


def run_distribution_review(bbl: str, bin_: str, work_type: str) -> list[dict[str, Any]]:
    """Run all department distribution checks against live NYC Open Data."""
    reviews = _run(_engine.run_all(bbl=bbl, bin_=bin_, work_type=work_type))
    return [review.model_dump(mode="json") for review in reviews]


zoning_agent = Agent(
    name="zoning_agent",
    description="NYC zoning review using PLUTO.",
    instruction="Use lookup_pluto to report zoning district and land use for the case BBL.",
    tools=[FunctionTool(func=lookup_pluto)],
)

building_agent = Agent(
    name="building_agent",
    description="DOB permit and violation review.",
    instruction="Use lookup_permits to summarize permit history for the BBL.",
    tools=[FunctionTool(func=lookup_permits)],
)

distribution_agent = Agent(
    name="distribution_agent",
    description="Runs full cross-department distribution against NYC Open Data.",
    instruction="Use run_distribution_review with the case BBL, BIN, and work type.",
    tools=[FunctionTool(func=run_distribution_review)],
)

critic_agent = Agent(
    name="critic_agent",
    description="Validates department reviews follow cite-or-reject policy.",
    instruction=(
        "Review distribution results. Any FAIL status must include ordinance citations. "
        "Reject uncited failures and recommend re-route to the originating department."
    ),
    tools=[FunctionTool(func=run_distribution_review)],
)

root_agent = Agent(
    name="permit_orchestrator",
    description="NYC permit review orchestrator for municipal clerks.",
    instruction=(
        "Coordinate department reviews for NYC building permits. "
        "Delegate to distribution_agent for a full live Open Data review, "
        "then critic_agent to validate citations."
    ),
    sub_agents=[zoning_agent, building_agent, distribution_agent, critic_agent],
)
