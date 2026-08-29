"""Fleet catalog contracts — 8 agents, Gemini 3.5, MCP tool zoning."""

from __future__ import annotations

import unittest

from permit_pilot_core.platform.fleet import FLEET, MCP_TOOL_CATALOG, fleet_by_name
from permit_pilot_core.settings import get_settings


class FleetCatalogTest(unittest.TestCase):
    def test_eight_named_agents(self) -> None:
        names = [agent.name for agent in FLEET]
        self.assertEqual(len(names), 8)
        self.assertEqual(len(set(names)), 8)
        self.assertIn("permit_orchestrator", names)
        self.assertIn("critic_agent", names)

    def test_model_is_gemini_35(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.vertex_model, "gemini-3.5-flash")
        self.assertEqual(settings.vertex_location, "global")

    def test_tools_come_from_mcp_catalog(self) -> None:
        for agent in FLEET:
            self.assertTrue(agent.tools, agent.name)
            extra = set(agent.tools) - MCP_TOOL_CATALOG
            self.assertFalse(extra, extra)

    def test_zoning_cannot_reach_hpd(self) -> None:
        zoning = fleet_by_name()["zoning_agent"]
        self.assertNotIn("lookup_hpd_violations", zoning.tools)
        self.assertIn("lookup_pluto", zoning.tools)

    def test_orchestrator_does_not_hold_every_lookup(self) -> None:
        orch = fleet_by_name()["permit_orchestrator"]
        self.assertNotIn("lookup_hpd_violations", orch.tools)
        self.assertNotIn("persist_review", orch.tools)
        self.assertIn("suggest_routing_plan", orch.tools)
        self.assertIn("draft_claim", orch.tools)

    def test_housing_cannot_reach_pluto(self) -> None:
        housing = fleet_by_name()["housing_agent"]
        self.assertNotIn("lookup_pluto", housing.tools)
        self.assertIn("lookup_hpd_violations", housing.tools)

    def test_critic_is_grounded_in_validate_citations(self) -> None:
        critic = fleet_by_name()["critic_agent"]
        self.assertIn("validate_citations", critic.tools)
        self.assertIn("get_ordinance_section", critic.tools)
        self.assertIn("persist_review", critic.tools)

    def test_specialists_do_not_fail_on_counts(self) -> None:
        for name in ("building_agent", "fire_agent", "utilities_agent", "housing_agent"):
            instruction = fleet_by_name()[name].instruction.lower()
            self.assertNotIn("fail when", instruction)
            self.assertIn("not automatic fail", instruction)


if __name__ == "__main__":
    unittest.main()
