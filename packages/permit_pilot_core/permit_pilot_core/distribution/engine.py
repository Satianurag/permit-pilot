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

_BUILDING_FAIL_CITATION = Citation(
    code="1 RCNY 101-07",
    excerpt="Open DOB violations must be resolved or dismissed before permit approval.",
    source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
)
_FIRE_FAIL_CITATION = Citation(
    code="FC 901.7",
    excerpt="Open fire code violations require correction or documented clearance before approval.",
    source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
)
_HOUSING_FAIL_CITATION = Citation(
    code="HMC §27-2115",
    excerpt="Class A or B HPD violations must be corrected before related permit work proceeds.",
    source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
)


def _house_number(address: str) -> str:
    token = address.strip().split(" ", 1)[0]
    return token.replace("'", "''")


def _now() -> datetime:
    return datetime.now(UTC)


def _is_active_dob_violation(row: dict) -> bool:
    category = str(row.get("violation_category", "")).upper()
    if "ACTIVE" in category:
        return True
    if category and "CLOSED" in category:
        return False
    disposition = str(row.get("disposition_date", "")).strip()
    return not disposition


def _is_open_hpd_violation(row: dict) -> bool:
    approved = str(row.get("approveddate", "")).strip()
    if approved:
        return False
    violation_class = str(row.get("class", "")).upper()
    return violation_class in {"A", "B", "C", "I"} or not approved


def _is_open_fdny_violation(row: dict) -> bool:
    status = str(row.get("violation_status", row.get("status", ""))).upper()
    if not status:
        return False
    return status not in {"CLOSED", "DISMISSED", "RESOLVED", "PAID"}


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
            await self.review_housing(bin_=bin_),
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
        active_violations = [v for v in violations if _is_active_dob_violation(v)]
        if active_violations:
            status = ReviewStatus.FAIL
            summary = f"{len(active_violations)} active DOB violation(s) on BIN — must be resolved before approval."
            citations = [_BUILDING_FAIL_CITATION]
        else:
            status = ReviewStatus.PASS
            summary = f"{len(permits)} permits on record; no active DOB violations on BIN."
            citations = []
        return DepartmentReview(
            department=Department.BUILDING,
            status=status,
            summary=summary,
            findings=[
                f"Permit rows on BBL: {len(permits)}",
                f"Filing rows on BIN: {len(filings)}",
                f"Active DOB violations on BIN: {len(active_violations)}",
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
                    label="active_violation_count",
                    value=len(active_violations),
                ),
            ],
            citations=citations,
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
        open_rows = [row for row in rows if _is_open_fdny_violation(row)]
        if open_rows:
            status = ReviewStatus.FAIL
            summary = f"{len(open_rows)} open FDNY violation record(s) on BIN."
            citations = [_FIRE_FAIL_CITATION]
        else:
            status = ReviewStatus.PASS
            historical = len(rows)
            summary = (
                f"No open FDNY violations on BIN."
                if historical == 0
                else f"No open FDNY violations; {historical} historical record(s) on file."
            )
            citations = []
        return DepartmentReview(
            department=Department.FIRE,
            status=status,
            summary=summary,
            findings=[
                f"FDNY records on BIN: {len(rows)}",
                f"Open FDNY violations: {len(open_rows)}",
            ],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="bi53-yph3",
                    label="open_violation_count",
                    value=len(open_rows),
                )
            ],
            citations=citations,
            updated_at=_now(),
        )

    async def review_housing(self, *, bin_: str) -> DepartmentReview:
        if not bin_:
            return DepartmentReview(
                department=Department.HOUSING,
                status=ReviewStatus.NEEDS_INFO,
                summary="BIN required for HPD violation lookup.",
                updated_at=_now(),
            )
        rows = await self._socrata.hpd_violations_by_bin(bin_)
        open_rows = [row for row in rows if _is_open_hpd_violation(row)]
        class_a = [row for row in open_rows if str(row.get("class", "")).upper() == "A"]
        if class_a:
            status = ReviewStatus.FAIL
            summary = f"{len(class_a)} open Class A HPD violation(s) on BIN."
            citations = [_HOUSING_FAIL_CITATION]
        elif open_rows:
            status = ReviewStatus.NEEDS_INFO
            summary = f"{len(open_rows)} open HPD violation(s) — confirm correction before approval."
            citations = []
        else:
            status = ReviewStatus.PASS
            summary = "No open HPD violations on BIN."
            citations = []
        return DepartmentReview(
            department=Department.HOUSING,
            status=status,
            summary=summary,
            findings=[
                f"HPD violation rows on BIN: {len(rows)}",
                f"Open HPD violations: {len(open_rows)}",
            ],
            evidence=[
                EvidenceItem(
                    source="NYC Open Data",
                    dataset_id="wvxf-dwi5",
                    label="open_hpd_violation_count",
                    value=len(open_rows),
                )
            ],
            citations=citations,
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
        citations = []
        if open_rows:
            citations.append(
                Citation(
                    code="DEP Rules",
                    excerpt="Open DEP ECB violations must be resolved before permit approval.",
                    source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
                )
            )
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
            citations=citations,
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
                    source_url="https://github.com/BetaNYC/nyc-charter-laws-rules",
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

    async def related_permits(self, *, bbl: str, bin_: str) -> list[dict]:
        permits = await self._socrata.permits_by_bbl(bbl)
        if bin_:
            permits = permits + await self._socrata.permits_by_bin(bin_)
        seen: set[str] = set()
        rows: list[dict] = []
        for row in permits:
            key = str(row.get("job__") or row.get("job_") or row.get("job_number") or row.get("permit_si_no") or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            rows.append(row)
        return rows[:25]

    async def parcel_context(self, *, bbl: str) -> dict:
        rows = await self._socrata.pluto_by_bbl(bbl, limit=1)
        if not rows:
            return {}
        lot = rows[0]
        lat = lot.get("latitude")
        lon = lot.get("longitude")
        district = lot.get("zonedist1") or lot.get("zonedist")
        map_url = None
        if lat and lon:
            map_url = f"https://www.google.com/maps?q={lat},{lon}"
        return {
            "latitude": float(lat) if lat else None,
            "longitude": float(lon) if lon else None,
            "map_url": map_url,
            "zoning_district": str(district) if district else None,
        }
