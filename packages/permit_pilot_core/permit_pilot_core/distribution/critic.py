"""Cite-or-reject critic policy. Used by MCP validate_citations and engine fallback."""

from __future__ import annotations

from datetime import UTC, datetime

from permit_pilot_core.distribution.ordinance import citation_resolves, get_section
from permit_pilot_core.models import Citation, Department, DepartmentReview, EvidenceItem, ReviewStatus
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


def _count(review: DepartmentReview, label: str) -> int | None:
    for item in review.evidence:
        if item.label == label:
            try:
                return int(item.value)
            except (TypeError, ValueError):
                return None
    return None


def critic_findings(reviews: list[DepartmentReview]) -> dict[str, list[str]]:
    failures = [r for r in reviews if r.department != Department.CRITIC and r.status == ReviewStatus.FAIL]
    uncited = [r.department.value for r in failures if not r.citations]
    pass_without_evidence = [
        r.department.value
        for r in reviews
        if r.department != Department.CRITIC and r.status == ReviewStatus.PASS and not r.evidence
    ]
    unknown_codes: list[str] = []
    contradictions: list[str] = []
    unresolved: list[str] = []
    for review in reviews:
        if review.department == Department.CRITIC:
            continue
        for citation in review.citations:
            section = get_section(citation.code)
            if not section.get("found") and not citation_resolves(citation.code):
                unknown_codes.append(f"{review.department.value}: {citation.code}")
                unresolved.append(citation.code)
        active = _count(review, "active_violation_count")
        open_fdny = _count(review, "open_violation_count")
        class_a = _count(review, "open_class_a_count")
        dep = _count(review, "open_dep_ecb_count")
        if review.status == ReviewStatus.PASS:
            if active and active > 0:
                contradictions.append(f"{review.department.value}: PASS with active_violation_count={active}")
            if open_fdny and open_fdny > 0:
                contradictions.append(f"{review.department.value}: PASS with open_violation_count={open_fdny}")
            if class_a and class_a > 0:
                contradictions.append(f"{review.department.value}: PASS with open_class_a_count={class_a}")
            if dep and dep > 0:
                contradictions.append(f"{review.department.value}: PASS with open_dep_ecb_count={dep}")
    return {
        "uncited_failures": uncited,
        "pass_without_evidence": pass_without_evidence,
        "unknown_codes": unknown_codes,
        "contradictions": contradictions,
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
            summary=f"Rejected {len(findings['uncited_failures'])} failure(s) without citations: {depts}.",
            findings=["Cite-or-reject: FAIL reviews must include ordinance citations.", f"Departments: {depts}"],
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

    if findings["contradictions"]:
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.FAIL,
            summary="Rejected PASS that contradicts live evidence counts.",
            findings=["Evidence counts must support the stated status.", *findings["contradictions"]],
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
        summary="All failure findings include citations; evidence and codes validated against the ordinance corpus.",
        findings=[f"Reviewed {len(reviews)} department outputs."],
        evidence=[policy],
        updated_at=_now(),
        generated_by=generated_by,
        model=get_settings().vertex_model,
    )
