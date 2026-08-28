"""Golden-set evaluation over live NYC Open Data BBLs used in production seeds."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import httpx

from permit_pilot_core.distribution.routing import plan_departments
from permit_pilot_core.models import Department, ReviewStatus
from permit_pilot_core.platform.fleet import fleet_by_name


class AgentTrajectoryEval(unittest.TestCase):
    """Eval contracts for the canonical coordinator fleet, not the engine fallback."""

    def test_parsons_building_calls_violations_then_persist(self) -> None:
        building = fleet_by_name()["building_agent"]
        self.assertIn("lookup_dob_violations", building.tools)
        self.assertIn("persist_review", building.tools)
        self.assertLess(building.tools.index("lookup_dob_violations"), building.tools.index("persist_review"))

    def test_macon_plumbing_routing_omits_landmarks(self) -> None:
        plan = plan_departments(
            work_type="Plumbing modifications to existing kitchen",
            bin_="3040031",
            pluto={"facts": {"histdist": "", "in_landmark_context": False}},
        )
        self.assertNotIn("landmarks", plan["departments"])
        self.assertIn("landmarks", plan["skipped"])

    def test_178_street_routing_includes_landmarks_when_complete(self) -> None:
        plan = plan_departments(
            work_type="Alteration",
            bin_="4117367",
            pluto={"facts": {"histdist": "", "in_landmark_context": False}},
        )
        self.assertIn("landmarks", plan["departments"])


class PlutoGoldenSet(unittest.IsolatedAsyncioTestCase):
    async def test_macon_street_is_r5b_on_pluto(self) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://data.cityofnewyork.us/resource/64uk-42ks.json",
                params={"$where": "bbl='3014930048'", "$limit": "1"},
            )
            response.raise_for_status()
            rows = response.json()
        self.assertTrue(rows, "PLUTO returned no row for 761 Macon Street")
        zoning = str(rows[0].get("zonedist1") or "")
        self.assertEqual(zoning, "R5B")


class CriticGrounding(unittest.TestCase):
    def test_critic_rejects_uncited_failure(self) -> None:
        from datetime import UTC, datetime

        from permit_pilot_core.distribution.critic import review_critic
        from permit_pilot_core.models import DepartmentReview
        from permit_pilot_core.settings import get_settings

        env = {**os.environ, "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT") or "eval-project"}
        with mock.patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            fake = DepartmentReview(
                department=Department.BUILDING,
                status=ReviewStatus.FAIL,
                summary="Uncited failure",
                updated_at=datetime.now(UTC),
            )
            critic = review_critic([fake])
            self.assertEqual(critic.status, ReviewStatus.FAIL)
            get_settings.cache_clear()


class LiveEvidenceAndRouting(unittest.IsolatedAsyncioTestCase):
    """Golden BBLs against live NYC Open Data + the coordinator routing plan, not DistributionEngine."""

    async def test_macon_live_pluto_has_no_status_and_skips_lpc(self) -> None:
        from permit_pilot_core.distribution.evidence import EvidenceClient

        try:
            payload = await EvidenceClient().lookup_pluto("3014930048")
        except Exception:
            self.skipTest("NYC Open Data unreachable")
            return
        self.assertNotIn("status", payload)
        self.assertEqual(payload["facts"]["zonedist1"], "R5B")
        plan = plan_departments(
            work_type="Plumbing modifications to existing kitchen",
            bin_="3040031",
            pluto=payload,
        )
        self.assertNotIn("landmarks", plan["departments"])
        self.assertIn("landmarks", plan["skipped"])

    async def test_parsons_demolition_routes_building_and_landmarks(self) -> None:
        plan = plan_departments(
            work_type="Construction Fence — Demolition of 3 story building",
            bin_="4117367",
            pluto={"facts": {"histdist": "", "in_landmark_context": False}},
        )
        self.assertIn("building", plan["departments"])
        self.assertIn("landmarks", plan["departments"])
        building = fleet_by_name()["building_agent"]
        self.assertIn("lookup_dob_violations", building.tools)
        self.assertIn("persist_review", building.tools)


if __name__ == "__main__":
    unittest.main()
