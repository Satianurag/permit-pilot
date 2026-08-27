"""Golden-set evaluation over live NYC Open Data BBLs used in production seeds."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import httpx

from permit_pilot_core.models import Department, ReviewStatus
from permit_pilot_core.seeds import REAL_NYC_CASES


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


class CriticGrounding(unittest.IsolatedAsyncioTestCase):
    async def test_critic_rejects_uncited_failure(self) -> None:
        from datetime import UTC, datetime

        from permit_pilot_core.distribution.engine import DistributionEngine
        from permit_pilot_core.models import DepartmentReview
        from permit_pilot_core.settings import get_settings

        env = {**os.environ, "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT") or "eval-project"}
        with mock.patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            engine = DistributionEngine()
            fake = DepartmentReview(
                department=Department.BUILDING,
                status=ReviewStatus.FAIL,
                summary="Uncited failure",
                updated_at=datetime.now(UTC),
            )
            critic = await engine.review_critic(reviews=[fake])
            self.assertEqual(critic.status, ReviewStatus.FAIL)
            get_settings.cache_clear()


@unittest.skipUnless(os.environ.get("GOOGLE_CLOUD_PROJECT"), "Requires GOOGLE_CLOUD_PROJECT")
class LiveBblEvaluation(unittest.IsolatedAsyncioTestCase):
    async def test_each_reference_bbl_returns_department_reviews(self) -> None:
        from permit_pilot_core.distribution.engine import DistributionEngine

        engine = DistributionEngine()
        for payload in REAL_NYC_CASES:
            reviews = await engine.run_all(bbl=payload.bbl, bin_=payload.bin, work_type=payload.work_type)
            depts = {review.department for review in reviews}
            self.assertIn(Department.ZONING, depts)
            self.assertIn(Department.CRITIC, depts)
            for review in reviews:
                self.assertIn(review.status, set(ReviewStatus))
                if review.status == ReviewStatus.FAIL:
                    self.assertTrue(review.citations, f"{payload.bbl} {review.department} fail without citation")


if __name__ == "__main__":
    unittest.main()
