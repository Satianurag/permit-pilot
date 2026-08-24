import unittest
from datetime import datetime, timezone

from permit_pilot_core.decisions import approval_block_message, failed_review_departments
from permit_pilot_core.models import Department, DepartmentReview, ReviewStatus


def _review(department: Department, status: ReviewStatus) -> DepartmentReview:
    return DepartmentReview(
        department=department,
        status=status,
        summary=status.value,
        updated_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )


class ApprovalGateTests(unittest.TestCase):
    def test_blocks_without_override(self) -> None:
        msg = approval_block_message(["landmarks", "dep"], False)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("landmarks", msg)
        self.assertIn("dep", msg)

    def test_allows_override(self) -> None:
        self.assertIsNone(approval_block_message(["landmarks"], True))

    def test_allows_clean_reviews(self) -> None:
        self.assertIsNone(approval_block_message([], False))

    def test_failed_departments_from_reviews(self) -> None:
        reviews = [
            _review(Department.ZONING, ReviewStatus.PASS),
            _review(Department.LANDMARKS, ReviewStatus.FAIL),
        ]
        self.assertEqual(failed_review_departments(reviews), ["landmarks"])


if __name__ == "__main__":
    unittest.main()
