"""MCP evidence tools return facts, not verdicts. Critic and routing are testable without GCP."""

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from permit_pilot_core.distribution.completeness import scan_case
from permit_pilot_core.distribution.critic import review_critic
from permit_pilot_core.distribution.ordinance import get_section, search_ordinance
from permit_pilot_core.distribution.routing import plan_departments
from permit_pilot_core.models import Case, CaseStatus, Citation, Department, DepartmentReview, EvidenceItem, ReviewStatus


def _review(**kwargs) -> DepartmentReview:
    defaults = dict(
        department=Department.BUILDING,
        status=ReviewStatus.FAIL,
        summary="fail",
        findings=[],
        evidence=[],
        citations=[],
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return DepartmentReview(**defaults)


class OrdinanceCorpusTest(unittest.TestCase):
    def test_get_section_resolves_admin_code(self) -> None:
        section = get_section("NYC Admin Code §28-105")
        self.assertTrue(section["found"])
        self.assertIn("permit", section["text"].lower())

    def test_search_returns_ranked_hits(self) -> None:
        results = search_ordinance("landmarks demolition")
        self.assertTrue(results)
        self.assertTrue(any("25-305" in item["citation"] or "landmark" in item["heading"].lower() for item in results))


class RoutingPlanTest(unittest.TestCase):
    def test_plumbing_skips_landmarks_without_histdist(self) -> None:
        plan = plan_departments(
            work_type="Plumbing modifications to existing kitchen",
            bin_="3040031",
            pluto={"facts": {"histdist": "", "in_landmark_context": False}},
        )
        self.assertNotIn("landmarks", plan["departments"])
        self.assertIn("landmarks", plan["skipped"])

    def test_demolition_includes_landmarks(self) -> None:
        plan = plan_departments(
            work_type="Construction Fence — Demolition of 3 story building",
            bin_="4117367",
            pluto={"facts": {"histdist": "", "in_landmark_context": False}},
        )
        self.assertIn("landmarks", plan["departments"])

    def test_incomplete_skips_all_technical(self) -> None:
        plan = plan_departments(work_type="Alteration", bin_="", complete_enough=False)
        self.assertEqual(plan["departments"], [])
        self.assertFalse(plan["include_critic"])


class CompletenessTest(unittest.TestCase):
    def test_missing_bin_is_incomplete(self) -> None:
        case = Case(
            id="x",
            address="112-08 178 STREET, QUEENS",
            bbl="4103000034",
            bin="",
            work_type="Alteration",
            owner="",
            status=CaseStatus.IN_REVIEW,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        scan = scan_case(case)
        self.assertFalse(scan.complete_enough)
        self.assertIn("BIN", scan.missing)


class CriticPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "permit-pilot-test")

    def test_uncited_failure_is_rejected(self) -> None:
        critic = review_critic([_review()])
        self.assertEqual(critic.status, ReviewStatus.FAIL)

    def test_contradiction_pass_with_active_violations(self) -> None:
        critic = review_critic(
            [
                _review(
                    status=ReviewStatus.PASS,
                    summary="pass",
                    citations=[Citation(code="1 RCNY 101-07", excerpt="x")],
                    evidence=[
                        EvidenceItem(
                            source="NYC Open Data",
                            dataset_id="3h2n-5cm9",
                            label="active_violation_count",
                            value=12,
                        )
                    ],
                )
            ]
        )
        self.assertEqual(critic.status, ReviewStatus.FAIL)
        self.assertIn("contradict", critic.summary.lower())

    def test_unknown_code_is_rejected(self) -> None:
        critic = review_critic(
            [
                _review(
                    citations=[Citation(code="MADE-UP-99", excerpt="nope")],
                    evidence=[EvidenceItem(source="NYC Open Data", dataset_id="x", label="n", value=1)],
                )
            ]
        )
        self.assertEqual(critic.status, ReviewStatus.FAIL)


class EvidenceLookupShapeTest(unittest.IsolatedAsyncioTestCase):
    async def test_lookup_pluto_has_no_status(self) -> None:
        from permit_pilot_core.distribution.evidence import EvidenceClient

        client = EvidenceClient()
        with patch.object(client._socrata, "pluto_by_bbl", new=AsyncMock(return_value=[{"zonedist1": "R5B", "bbl": "3014930048"}])):
            payload = await client.lookup_pluto("3014930048")
        self.assertNotIn("status", payload)
        self.assertEqual(payload["facts"]["zonedist1"], "R5B")
        self.assertEqual(payload["source"], "NYC Open Data")

    async def test_live_macon_pluto_has_no_status(self) -> None:
        import httpx
        from permit_pilot_core.distribution.evidence import EvidenceClient

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://data.cityofnewyork.us/resource/64uk-42ks.json",
                    params={"$where": "bbl='3014930048'", "$limit": "1"},
                )
                response.raise_for_status()
        except Exception:
            self.skipTest("NYC Open Data unreachable")
            return
        payload = await EvidenceClient().lookup_pluto("3014930048")
        self.assertNotIn("status", payload)
        self.assertEqual(payload["facts"]["zonedist1"], "R5B")


class GatewayFingerprintTest(unittest.TestCase):
    def test_tampered_fingerprint_is_rejected(self) -> None:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "permit-pilot-test")
        from permit_pilot_core.platform.gateway import fingerprint_allowed, signed_fingerprint
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()
        name = "zoning_agent"
        good = signed_fingerprint(name)
        self.assertTrue(fingerprint_allowed(name, good))
        self.assertFalse(fingerprint_allowed(name, f"{good}x"))
        self.assertFalse(fingerprint_allowed(name, ""))


class CriticRerouteTest(unittest.TestCase):
    def test_offenders_are_named_for_loop_reroute(self) -> None:
        from permit_pilot_core.fleet_runner import critic_offenders

        critic = _review(
            department=Department.CRITIC,
            summary="Rejected PASS that contradicts live evidence counts.",
            findings=["building: PASS with active_violation_count=12"],
        )
        self.assertEqual(critic_offenders(critic), ["building"])


class HitlDraftDoesNotApproveTest(unittest.TestCase):
    def test_pending_hitl_payload_is_unconfirmed(self) -> None:
        from permit_pilot_core.models import PendingHitl

        pending = PendingHitl(kind="record_decision", payload={"decision": "approve"}, confirmed=False)
        self.assertFalse(pending.confirmed)
        self.assertEqual(pending.kind, "record_decision")


class ResumeSkipTest(unittest.TestCase):
    def test_resume_skips_completed_departments(self) -> None:
        from permit_pilot_core.fleet_runner import _resume_targets
        from permit_pilot_core.models import DepartmentStep

        class _Store:
            def list_workflow_steps(self, _case_id: str) -> list[DepartmentStep]:
                return [DepartmentStep(name="distribution", department=Department.ZONING, status="completed")]

            def list_distribution(self, _case_id: str) -> list:
                return []

        remaining = _resume_targets(_Store(), "case", ["zoning", "building"], reason="resume")
        self.assertEqual(remaining, ["building"])


if __name__ == "__main__":
    unittest.main()
