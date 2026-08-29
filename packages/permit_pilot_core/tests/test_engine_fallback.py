"""Engine fallback never issues PASS/FAIL verdicts — evidence only."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from permit_pilot_core.distribution.engine import FALLBACK_SUMMARY, GENERATED_BY, DistributionEngine
from permit_pilot_core.models import Department, ReviewStatus


class EngineFallbackPolicyTest(unittest.IsolatedAsyncioTestCase):
    async def test_building_with_active_violations_is_needs_info(self) -> None:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "permit-pilot-test")
        engine = DistributionEngine()
        permits = {"dataset_id": "rbx6-tga4", "facts": {"permit_count": 2}, "rows": []}
        violations = {
            "dataset_id": "855j-jady",
            "facts": {"active_violation_count": 12},
            "rows": [{"description": "ELEVATOR — CERTIFICATE EXPIRED", "violation_type": "ELEVATOR"}],
            "note": "Read description",
        }
        with (
            patch.object(engine._evidence, "lookup_dob_permits", new=AsyncMock(return_value=permits)),
            patch.object(engine._evidence, "lookup_dob_violations", new=AsyncMock(return_value=violations)),
        ):
            review = await engine.review_building(bbl="4051980021", bin_="4117367")
        self.assertEqual(review.status, ReviewStatus.NEEDS_INFO)
        self.assertEqual(review.generated_by, GENERATED_BY)
        self.assertEqual(review.summary, FALLBACK_SUMMARY)
        self.assertTrue(review.evidence)
        self.assertEqual(review.department, Department.BUILDING)
        self.assertFalse(review.objections)
