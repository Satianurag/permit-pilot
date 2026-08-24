from permit_pilot_core.models import DepartmentReview, ReviewStatus


def failed_review_departments(reviews: list[DepartmentReview]) -> list[str]:
    return [review.department.value for review in reviews if review.status == ReviewStatus.FAIL]


def approval_block_message(failed: list[str], override: bool) -> str | None:
    """Clerks cannot approve failed reviews unless they record an override."""
    if failed and not override:
        depts = ", ".join(failed)
        return (
            f"Cannot approve while reviews failed ({depts}). "
            "Record an override in the clerk note, or request changes."
        )
    return None


failed_review_departments = failed_review_departments
approval_block_message = approval_block_message
