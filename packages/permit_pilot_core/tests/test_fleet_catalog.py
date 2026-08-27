"""Fleet catalog contracts — 8 agents, Gemini 3.5, MCP tool zoning."""

from __future__ import annotations

import unittest

from permit_pilot_core.platform.fleet import FLEET, fleet_by_name
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
        allowed = {
            "lookup_pluto",
            "lookup_dob_permits",
            "lookup_dob_violations",
            "lookup_fdny_violations",
            "lookup_hpd_violations",
            "lookup_dep_ecb",
            "lookup_landmarks",
            "validate_citations",
            "persist_review",
        }
        for agent in FLEET:
            self.assertTrue(agent.tools, agent.name)
            extra = set(agent.tools) - allowed
            self.assertFalse(extra, extra)

    def test_zoning_cannot_reach_hpd(self) -> None:
        zoning = fleet_by_name()["zoning_agent"]
        self.assertNotIn("lookup_hpd_violations", zoning.tools)
        self.assertIn("lookup_pluto", zoning.tools)

    def test_housing_cannot_reach_pluto(self) -> None:
        housing = fleet_by_name()["housing_agent"]
        self.assertNotIn("lookup_pluto", housing.tools)
        self.assertIn("lookup_hpd_violations", housing.tools)

    def test_critic_is_grounded_in_validate_citations(self) -> None:
        critic = fleet_by_name()["critic_agent"]
        self.assertEqual(set(critic.tools), {"validate_citations", "persist_review"})


if __name__ == "__main__":
    unittest.main()
