"""Per-agent IAP CEL must not grant zoning the HPD tool."""

from __future__ import annotations

import unittest

from permit_pilot_core.platform.fleet import FLEET, fleet_by_name
from permit_pilot_core.platform.iap_bindings import (
    endpoint_egressor_bindings,
    mcp_egressor_bindings,
    tool_condition,
)


class IapBindingsTest(unittest.TestCase):
    def test_zoning_cel_excludes_hpd(self) -> None:
        zoning = fleet_by_name()["zoning_agent"]
        expression = tool_condition(zoning)["expression"]
        self.assertIn("lookup_pluto", expression)
        self.assertIn("persist_review", expression)
        self.assertNotIn("lookup_hpd_violations", expression)

    def test_housing_cel_excludes_pluto(self) -> None:
        housing = fleet_by_name()["housing_agent"]
        expression = tool_condition(housing)["expression"]
        self.assertIn("lookup_hpd_violations", expression)
        self.assertNotIn("lookup_pluto", expression)

    def test_mcp_bindings_one_per_agent(self) -> None:
        principals = {spec.name: f"principal://test/{spec.name}" for spec in FLEET}
        bindings = mcp_egressor_bindings(
            principals=principals,
            extra_members=["serviceAccount:api@example.com"],
        )
        self.assertEqual(len(bindings), 1 + len(FLEET))
        zoning = next(
            item
            for item in bindings
            if item.get("condition", {}).get("title") == "zoning_agent-tools"
        )
        self.assertNotIn(
            "lookup_hpd_violations", zoning["condition"]["expression"]
        )

    def test_critic_not_on_socrata_endpoint(self) -> None:
        principals = {spec.name: f"principal://test/{spec.name}" for spec in FLEET}
        bindings = endpoint_egressor_bindings(principals=principals)
        members = bindings[0]["members"]
        self.assertNotIn(principals["critic_agent"], members)
        self.assertIn(principals["zoning_agent"], members)
        self.assertIn(principals["permit_orchestrator"], members)


if __name__ == "__main__":
    unittest.main()
