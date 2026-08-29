"""Cite-or-reject critic policy. Used by MCP validate_citations and engine fallback."""

from __future__ import annotations

from datetime import UTC, datetime

from permit_pilot_core.distribution.ordinance import citation_resolves, get_section
from permit_pilot_core.models import (
    Citation,
    Department,
    DepartmentReview,
    EvidenceItem,
    ObjectionItem,
    ReviewStatus,
)
from permit_pilot_core.settings import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


def _policy_evidence() -> EvidenceItem:
    return EvidenceItem(
        source="Policy check",
        dataset_id="policy/cite-or-reject",
        label="policy_check",
        value="cite-or-reject",
    )


def _citation() -> Citation:
    return Citation(
        code="NYC Admin Code §28-105",
        excerpt="Department determinations must reference applicable code sections.",
        source_url=get_settings().citation_source_url,
    )


def _codes_on_review(review: DepartmentReview) -> list[str]:
    codes = [item.code.strip() for item in review.citations if item.code.strip()]
    codes.extend(item.code.strip() for item in review.objections if item.code.strip())
    return codes


def _uncited_objections(review: DepartmentReview) -> list[ObjectionItem]:
    return [item for item in review.open_objections() if not item.code.strip()]


def critic_findings(reviews: list[DepartmentReview]) -> dict[str, list[str]]:
    technical = [r for r in reviews if r.department != Department.CRITIC]
    uncited = [r.department.value for r in technical if r.status == ReviewStatus.FAIL and not r.citations]
    uncited.extend(
        r.department.value for r in technical if _uncited_objections(r) and r.department.value not in uncited
    )
    pass_without_evidence = [
        r.department.value for r in technical if r.status == ReviewStatus.PASS and not r.evidence
    ]
    pass_with_open_objections = [
        r.department.value for r in technical if r.status == ReviewStatus.PASS and r.open_objections()
    ]
    unknown_codes: list[str] = []
    unresolved: list[str] = []
    for review in technical:
        for code in _codes_on_review(review):
            section = get_section(code)
            if not section.get("found") and not citation_resolves(code):
                unknown_codes.append(f"{review.department.value}: {code}")
                unresolved.append(code)
    return {
        "uncited_failures": uncited,
        "pass_without_evidence": pass_without_evidence,
        "pass_with_open_objections": pass_with_open_objections,
        "unknown_codes": unknown_codes,
        "unresolved": unresolved,
    }


def review_critic(reviews: list[DepartmentReview], *, generated_by: str = "critic_agent") -> DepartmentReview:
    findings = critic_findings(reviews)
    policy = _policy_evidence()
    cite = _citation()

    if findings["uncited_failures"]:
        depts = ", ".join(findings["uncited_failures"])
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.FAIL,
            summary=f"Rejected {len(findings['uncited_failures'])} review(s) without citations: {depts}.",
            findings=[
                "Cite-or-reject: FAIL reviews and open objections must include ordinance citations.",
                f"Departments: {depts}",
            ],
            evidence=[policy],
            citations=[cite],
            updated_at=_now(),
            generated_by=generated_by,
            model=get_settings().vertex_model,
        )

    if findings["pass_without_evidence"]:
        depts = ", ".join(findings["pass_without_evidence"])
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.FAIL,
            summary=f"Rejected PASS without supporting evidence: {depts}.",
            findings=["PASS reviews must cite NYC Open Data evidence rows.", f"Departments: {depts}"],
            evidence=[policy],
            citations=[cite],
            updated_at=_now(),
            generated_by=generated_by,
            model=get_settings().vertex_model,
        )

    if findings["pass_with_open_objections"]:
        depts = ", ".join(findings["pass_with_open_objections"])
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.FAIL,
            summary=f"Rejected PASS that still has open objections: {depts}.",
            findings=[
                "Open objections mean the review is not PASS. Persist FAIL or NEEDS_INFO, or withdraw the objections.",
                f"Departments: {depts}",
            ],
            evidence=[policy],
            citations=[cite],
            updated_at=_now(),
            generated_by=generated_by,
            model=get_settings().vertex_model,
        )

    if findings["unknown_codes"]:
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.FAIL,
            summary="Rejected citation(s) that do not resolve in the ordinance corpus.",
            findings=["Call get_ordinance_section before accepting a code.", *findings["unknown_codes"]],
            evidence=[policy],
            citations=[cite],
            updated_at=_now(),
            generated_by=generated_by,
            model=get_settings().vertex_model,
        )

    return DepartmentReview(
        department=Department.CRITIC,
        status=ReviewStatus.PASS,
        summary="Citations and evidence checked. Existing violation counts are parcel context, not automatic FAIL.",
        findings=[f"Reviewed {len(reviews)} department outputs."],
        evidence=[policy],
        updated_at=_now(),
        generated_by=generated_by,
        model=get_settings().vertex_model,
    )
