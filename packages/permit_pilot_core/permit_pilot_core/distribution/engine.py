from __future__ import annotations

from datetime import UTC, datetime

from permit_pilot_core.models import (
    Citation,
    Department,
    DepartmentReview,
    EvidenceItem,
    ReviewStatus,
)
from permit_pilot_core.socrata.client import SocrataClient

BOROUGH_NAMES = {
    "MN": "MANHATTAN",
    "BX": "BRONX",
    "BK": "BROOKLYN",
    "QN": "QUEENS",
    "SI": "STATEN ISLAND",
}


def _house_number(address: str) -> str:
    token = address.strip().split(" ", 1)[0]
    return token.replace("'", "''")


def _now() -> datetime:
    return datetime.now(UTC)


class DistributionEngine:
    def __init__(self, socrata: SocrataClient | None = None) -> None:
        self._socrata = socrata or SocrataClient()

    async def run_departments(self, *, bbl: str, bin_: str, work_type: str) -> list[DepartmentReview]:
        return [
            await self.review_zoning(bbl=bbl),
            await self.review_building(bbl=bbl, bin_=bin_),
            await self.review_fire(bin_=bin_),
            await self.review_utilities(bbl=bbl, bin_=bin_),
            await self.review_landmarks(bbl=bbl, work_type=work_type),
        ]

    async def run_all(self, *, bbl: str, bin_: str, work_type: str) -> list[DepartmentReview]:
        reviews = await self.run_departments(bbl=bbl, bin_=bin_, work_type=work_type)
        reviews.append(await self.review_critic(reviews=reviews))
        return reviews

    async def review_zoning(self, *, bbl: str) -> DepartmentReview:
        rows = await self._socrata.pluto_by_bbl(bbl)
        if not rows:
            return DepartmentReview(
                department=Department.ZONING,
                status=ReviewStatus.NEEDS_INFO,
                summary="No PLUTO record found for this BBL.",
                updated_at=_now(),
            )
        lot = rows[0]
        district = lot.get("zonedist1") or lot.get("zonedist")
        landuse = lot.get("landuse")
        histdist = lot.get("histdist")
        findings = [
            f"Zoning district: {district}",
            f"Land use code: {landuse}",
            f"Historic district field: {histdist or 'none'}",
        ]
        evidence = [
            EvidenceItem(
                source="NYC Open Data",
                dataset_id="64uk-42ks",
                label="zonedist1",
                value=district,
            ),
            EvidenceItem(
                source="NYC Open Data",
                dataset_id="64uk-42ks",
                label="landuse",
                value=landuse,
            ),
        ]
        return DepartmentReview(
            department=Department.ZONING,
            status=ReviewStatus.PASS,
            summary=f"PLUTO confirms zoning district {district}.",
            findings=findings,
            evidence=evidence,
            updated_at=_now(),
        )

    async def review_building(self, *, bbl: str, bin_: str) -> DepartmentReview:
        permits = await self._socrata.permits_by_bbl(bbl)
        filings = await self._socrata.filings_by_bin(bin_) if bin_ else []
        violations = await self._socrata.dob_violations_by_bin(bin_) if bin_ else []
        open_violations = [
            v for v in violations if str(v.get("violation_category", "")).lower() != "closed"
        ]
        status = ReviewStatus.PASS if len(open_violations) < 20 else ReviewStatus.FAIL
        summary = (
            f"{len(permits)} permits on record; {len(open_violations)} open DOB violations."
        )
        return DepartmentReview(
            department=Department.BUILDING,
            status=status,
            summary=summary,
            findings=[
                f"Permit rows on BBL: {len(permits)}",
                f"Filing rows on BIN: {len(filings)}",
                f"Open DOB violations on BIN: {len(open_violations)}",
            ],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="rbx6-tga4",
                    label="permit_count",
                    value=len(permits),
                ),
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="3h2n-5cm9",
                    label="open_violation_count",
                    value=len(open_violations),
                ),
            ],
            updated_at=_now(),
        )

    async def review_fire(self, *, bin_: str) -> DepartmentReview:
        if not bin_:
            return DepartmentReview(
                department=Department.FIRE,
                status=ReviewStatus.NEEDS_INFO,
                summary="BIN required for FDNY violation lookup.",
                updated_at=_now(),
            )
        rows = await self._socrata.fdny_violations_by_bin(bin_)
        status = ReviewStatus.PASS if len(rows) == 0 else ReviewStatus.FAIL
        return DepartmentReview(
            department=Department.FIRE,
            status=status,
            summary=f"{len(rows)} FDNY violation records on BIN.",
            findings=[f"FDNY historical violations: {len(rows)}"],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="bi53-yph3",
                    label="violation_count",
                    value=len(rows),
                )
            ],
            updated_at=_now(),
        )

    async def review_utilities(self, *, bbl: str, bin_: str) -> DepartmentReview:
        pluto_rows = await self._socrata.pluto_by_bbl(bbl)
        if not pluto_rows:
            return DepartmentReview(
                department=Department.UTILITIES,
                status=ReviewStatus.NEEDS_INFO,
                summary="No PLUTO record found for DEP ECB lookup.",
                updated_at=_now(),
            )
        lot = pluto_rows[0]
        address = str(lot.get("address") or "")
        borough_code = str(lot.get("borough") or "")
        borough_name = BOROUGH_NAMES.get(borough_code.upper(), borough_code.upper())
        house = _house_number(address)
        if not house or not borough_name:
            return DepartmentReview(
                department=Department.UTILITIES,
                status=ReviewStatus.NEEDS_INFO,
                summary="Address and borough required for DEP ECB violation lookup.",
                updated_at=_now(),
            )
        rows = await self._socrata.dep_ecb_by_address(house=house, borough=borough_name)
        open_rows = [
            row
            for row in rows
            if str(row.get("compliance_status", "")).lower() not in {"dismissed", "paid in full"}
        ]
        status = ReviewStatus.PASS if len(open_rows) == 0 else ReviewStatus.FAIL
        return DepartmentReview(
            department=Department.UTILITIES,
            status=status,
            summary=f"{len(open_rows)} open DEP ECB violation records at {address}.",
            findings=[
                f"DEP ECB records for {address}, {borough_name}: {len(rows)} total",
                f"Open or penalty-due records: {len(open_rows)}",
            ],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="skr7-cxt3",
                    label="dep_ecb_record_count",
                    value=len(rows),
                ),
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="skr7-cxt3",
                    label="open_dep_ecb_count",
                    value=len(open_rows),
                ),
            ],
            updated_at=_now(),
        )

    async def review_landmarks(self, *, bbl: str, work_type: str) -> DepartmentReview:
        rows = await self._socrata.landmarks_by_bbl(bbl)
        pluto = await self._socrata.pluto_by_bbl(bbl)
        histdist = pluto[0].get("histdist") if pluto else None
        in_landmark = bool(rows) or bool(histdist)
        demolition = "demolition" in work_type.lower()
        if in_landmark and demolition:
            status = ReviewStatus.FAIL
            summary = "Property is in or adjacent to a landmark context; demolition requires LPC review."
            citations = [
                Citation(
                    code="NYC LPC",
                    excerpt="Work affecting landmark properties requires Landmarks Preservation Commission approval.",
                )
            ]
        elif in_landmark:
            status = ReviewStatus.NEEDS_INFO
            summary = "Landmark records present; confirm scope with LPC."
            citations = []
        else:
            status = ReviewStatus.PASS
            summary = "No LPC landmark records on this BBL."
            citations = []
        return DepartmentReview(
            department=Department.LANDMARKS,
            status=status,
            summary=summary,
            findings=[
                f"LPC dataset rows: {len(rows)}",
                f"PLUTO histdist: {histdist or 'none'}",
            ],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="gpmc-yuvp",
                    label="landmark_row_count",
                    value=len(rows),
                )
            ],
            citations=citations,
            updated_at=_now(),
        )

    async def review_critic(self, *, reviews: list[DepartmentReview]) -> DepartmentReview:
        failures = [r for r in reviews if r.status == ReviewStatus.FAIL]
        uncited_failures = [r for r in failures if not r.citations]
        if uncited_failures:
            depts = ", ".join(r.department.value for r in uncited_failures)
            return DepartmentReview(
                department=Department.CRITIC,
                status=ReviewStatus.FAIL,
                summary=f"Rejected {len(uncited_failures)} failure(s) without citations: {depts}.",
                findings=[
                    "Cite-or-reject policy: FAIL reviews must include ordinance citations.",
                    f"Departments missing citations: {depts}",
                ],
                evidence=[
                    EvidenceItem(
                        source="Permit Pilot Critic",
                        dataset_id="policy/cite-or-reject",
                        label="uncited_failures",
                        value=len(uncited_failures),
                    )
                ],
                citations=[
                    Citation(
                        code="NYC Admin Code §28-105",
                        excerpt="Department determinations must reference applicable code sections.",
                        source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
                    )
                ],
                updated_at=_now(),
            )
        return DepartmentReview(
            department=Department.CRITIC,
            status=ReviewStatus.PASS,
            summary="All failure findings include citations or no failures detected.",
            findings=[f"Reviewed {len(reviews)} department outputs."],
            evidence=[
                EvidenceItem(
                    source="Permit Pilot Critic",
                    dataset_id="policy/cite-or-reject",
                    label="departments_reviewed",
                    value=len(reviews),
                )
            ],
            updated_at=_now(),
        )
