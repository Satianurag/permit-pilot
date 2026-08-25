import unittest
from datetime import datetime, timezone

from permit_pilot_core.decisions import (
    approval_block_message,
    checking_departments,
    failed_review_departments,
    needs_info_departments,
)
from permit_pilot_core.models import Department, DepartmentReview, ReviewStatus


def _review(department: Department, status: ReviewStatus) -> DepartmentReview:
    return DepartmentReview(
        department=department,
        status=status,
        summary=status.value,
        updated_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )


class ApprovalGateTests(unittest.TestCase):
    def test_blocks_failed_without_override(self) -> None:
        msg = approval_block_message(
            failed=["landmarks", "dep"],
            needs_info=[],
            checking=[],
            override=False,
        )
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("landmarks", msg)

    def test_blocks_needs_info_without_override(self) -> None:
        msg = approval_block_message(
            failed=[],
            needs_info=["housing"],
            checking=[],
            override=False,
        )
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("housing", msg)

    def test_blocks_checking_without_override(self) -> None:
        msg = approval_block_message(
            failed=[],
            needs_info=[],
            checking=["zoning"],
            override=False,
        )
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("zoning", msg)

    def test_allows_override(self) -> None:
        self.assertIsNone(
            approval_block_message(
                failed=["landmarks"],
                needs_info=["housing"],
                checking=["zoning"],
                override=True,
            )
        )

    def test_allows_clean_reviews(self) -> None:
        self.assertIsNone(
            approval_block_message(failed=[], needs_info=[], checking=[], override=False)
        )

    def test_failed_departments_from_reviews(self) -> None:
        reviews = [
            _review(Department.ZONING, ReviewStatus.PASS),
            _review(Department.LANDMARKS, ReviewStatus.FAIL),
        ]
        self.assertEqual(failed_review_departments(reviews), ["landmarks"])

    def test_needs_info_departments_from_reviews(self) -> None:
        reviews = [
            _review(Department.HOUSING, ReviewStatus.NEEDS_INFO),
            _review(Department.CRITIC, ReviewStatus.FAIL),
        ]
        self.assertEqual(needs_info_departments(reviews), ["housing"])
        self.assertEqual(checking_departments(reviews), [])


if __name__ == "__main__":
    unittest.main()
