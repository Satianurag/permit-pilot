from permit_pilot_core.models import Department, DepartmentReview, ReviewStatus


def failed_review_departments(reviews: list[DepartmentReview]) -> list[str]:
    return [
        review.department.value
        for review in reviews
        if review.department != Department.CRITIC and review.status == ReviewStatus.FAIL
    ]


def needs_info_departments(reviews: list[DepartmentReview]) -> list[str]:
    return [
        review.department.value
        for review in reviews
        if review.department != Department.CRITIC and review.status == ReviewStatus.NEEDS_INFO
    ]


def checking_departments(reviews: list[DepartmentReview]) -> list[str]:
    return [
        review.department.value
        for review in reviews
        if review.department != Department.CRITIC and review.status == ReviewStatus.CHECKING
    ]


def approval_block_message(
    *,
    failed: list[str],
    needs_info: list[str],
    checking: list[str],
    override: bool,
) -> str | None:
    """Clerks cannot approve while distribution is incomplete unless they record an override."""
    if override:
        return None
    if checking:
        depts = ", ".join(checking)
        return (
            f"Cannot approve while department reviews are still running ({depts}). "
            "Wait for distribution to finish or request changes."
        )
    if failed:
        depts = ", ".join(failed)
        return (
            f"Cannot approve while reviews failed ({depts}). "
            "Record an override in the clerk note, or request changes."
        )
    if needs_info:
        depts = ", ".join(needs_info)
        return (
            f"Cannot approve while reviews need more information ({depts}). "
            "Record an override in the clerk note, or request changes."
        )
    return None
