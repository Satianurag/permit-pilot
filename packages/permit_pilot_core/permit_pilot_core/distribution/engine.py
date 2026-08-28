"""Engine fallback: evidence → labeled deterministic reviews when Agent Runtime is down."""

from __future__ import annotations

from datetime import UTC, datetime

from permit_pilot_core.distribution.critic import review_critic as critic_policy
from permit_pilot_core.distribution.evidence import EvidenceClient
from permit_pilot_core.distribution.ordinance import get_section
from permit_pilot_core.models import (
    Citation,
    Department,
    DepartmentReview,
    EvidenceItem,
    ReviewStatus,
)
from permit_pilot_core.socrata.client import SocrataClient
from permit_pilot_core.settings import get_settings

GENERATED_BY = "engine_fallback"


def _now() -> datetime:
    return datetime.now(UTC)


def _cite(code: str) -> Citation:
    section = get_section(code)
    excerpt = str(section.get("text") or "")[:240] if section.get("found") else code
    return Citation(code=code, excerpt=excerpt, source_url=get_settings().citation_source_url)


def _evidence_items(payload: dict) -> list[EvidenceItem]:
    dataset_id = str(payload.get("dataset_id") or "")
    items: list[EvidenceItem] = []
    for label, value in (payload.get("facts") or {}).items():
        items.append(EvidenceItem(source="NYC Open Data", dataset_id=dataset_id, label=str(label), value=value))
    return items


class DistributionEngine:
    def __init__(self, socrata: SocrataClient | None = None) -> None:
        self._socrata = socrata or SocrataClient()
        self._evidence = EvidenceClient(self._socrata)

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
        payload = await self._evidence.lookup_pluto(bbl)
        facts = payload.get("facts") or {}
        if not facts.get("found"):
            return DepartmentReview(
                department=Department.ZONING,
                status=ReviewStatus.NEEDS_INFO,
                summary="No PLUTO record found for this BBL.",
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        district = facts.get("zonedist1")
        return DepartmentReview(
            department=Department.ZONING,
            status=ReviewStatus.PASS,
            summary=f"PLUTO confirms zoning district {district}.",
            findings=[
                f"Zoning district: {district}",
                f"Land use code: {facts.get('landuse')}",
                f"Historic district field: {facts.get('histdist') or 'none'}",
            ],
            evidence=_evidence_items(payload),
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_building(self, *, bbl: str, bin_: str) -> DepartmentReview:
        permits = await self._evidence.lookup_dob_permits(bbl, bin_)
        violations = await self._evidence.lookup_dob_violations(bin_)
        active = int((violations.get("facts") or {}).get("active_violation_count") or 0)
        evidence = _evidence_items(permits) + _evidence_items(violations)
        if active:
            return DepartmentReview(
                department=Department.BUILDING,
                status=ReviewStatus.FAIL,
                summary=f"{active} active DOB violation(s) on BIN — must be resolved before approval.",
                findings=[f"Active DOB violations on BIN: {active}"],
                evidence=evidence,
                citations=[_cite("1 RCNY 101-07")],
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        permit_count = int((permits.get("facts") or {}).get("permit_count") or 0)
        return DepartmentReview(
            department=Department.BUILDING,
            status=ReviewStatus.PASS,
            summary=f"{permit_count} permits on record; no active DOB violations on BIN.",
            findings=[f"Permit rows on BBL: {permit_count}", f"Active DOB violations on BIN: {active}"],
            evidence=evidence,
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_fire(self, *, bin_: str) -> DepartmentReview:
        payload = await self._evidence.lookup_fdny_violations(bin_)
        facts = payload.get("facts") or {}
        if not facts.get("bin_present"):
            return DepartmentReview(
                department=Department.FIRE,
                status=ReviewStatus.NEEDS_INFO,
                summary="BIN required for FDNY violation lookup.",
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        open_count = int(facts.get("open_violation_count") or 0)
        if open_count:
            return DepartmentReview(
                department=Department.FIRE,
                status=ReviewStatus.FAIL,
                summary=f"{open_count} open FDNY violation record(s) on BIN.",
                findings=[f"Open FDNY violations: {open_count}"],
                evidence=_evidence_items(payload),
                citations=[_cite("FC 901.7")],
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        return DepartmentReview(
            department=Department.FIRE,
            status=ReviewStatus.PASS,
            summary="No open FDNY violations on BIN.",
            findings=[f"FDNY records on BIN: {facts.get('record_count')}"],
            evidence=_evidence_items(payload),
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_housing(self, *, bin_: str) -> DepartmentReview:
        payload = await self._evidence.lookup_hpd_violations(bin_)
        facts = payload.get("facts") or {}
        if not facts.get("bin_present"):
            return DepartmentReview(
                department=Department.HOUSING,
                status=ReviewStatus.NEEDS_INFO,
                summary="BIN required for HPD violation lookup.",
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        class_a = int(facts.get("open_class_a_count") or 0)
        open_rows = int(facts.get("open_hpd_violation_count") or 0)
        if class_a:
            return DepartmentReview(
                department=Department.HOUSING,
                status=ReviewStatus.FAIL,
                summary=f"{class_a} open Class A HPD violation(s) on BIN.",
                findings=[f"Open HPD violations: {open_rows}"],
                evidence=_evidence_items(payload),
                citations=[_cite("HMC §27-2115")],
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        if open_rows:
            return DepartmentReview(
                department=Department.HOUSING,
                status=ReviewStatus.NEEDS_INFO,
                summary=f"{open_rows} open HPD violation(s) — confirm correction before approval.",
                findings=[f"Open HPD violations: {open_rows}"],
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        return DepartmentReview(
            department=Department.HOUSING,
            status=ReviewStatus.PASS,
            summary="No open HPD violations on BIN.",
            evidence=_evidence_items(payload),
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_utilities(self, *, bbl: str, bin_: str) -> DepartmentReview:
        payload = await self._evidence.lookup_dep_ecb(bbl, bin_)
        facts = payload.get("facts") or {}
        if not facts.get("found"):
            return DepartmentReview(
                department=Department.UTILITIES,
                status=ReviewStatus.NEEDS_INFO,
                summary=str(payload.get("note") or "DEP ECB lookup needs more parcel context."),
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        open_count = int(facts.get("open_dep_ecb_count") or 0)
        address = facts.get("address") or bbl
        if open_count:
            return DepartmentReview(
                department=Department.UTILITIES,
                status=ReviewStatus.FAIL,
                summary=f"{open_count} open DEP ECB violation records at {address}.",
                findings=[f"Open or penalty-due records: {open_count}"],
                evidence=_evidence_items(payload),
                citations=[_cite("DEP Rules")],
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        return DepartmentReview(
            department=Department.UTILITIES,
            status=ReviewStatus.PASS,
            summary=f"0 open DEP ECB violation records at {address}.",
            evidence=_evidence_items(payload),
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_landmarks(self, *, bbl: str, work_type: str) -> DepartmentReview:
        payload = await self._evidence.lookup_landmarks(bbl, work_type)
        facts = payload.get("facts") or {}
        in_landmark = bool(facts.get("in_landmark_context"))
        demolition = bool(facts.get("demolition"))
        if in_landmark and demolition:
            return DepartmentReview(
                department=Department.LANDMARKS,
                status=ReviewStatus.FAIL,
                summary="Property is in or adjacent to a landmark context; demolition requires LPC review.",
                findings=[f"LPC dataset rows: {facts.get('landmark_row_count')}", f"PLUTO histdist: {facts.get('histdist') or 'none'}"],
                evidence=_evidence_items(payload),
                citations=[_cite("NYC LPC")],
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        if in_landmark:
            return DepartmentReview(
                department=Department.LANDMARKS,
                status=ReviewStatus.NEEDS_INFO,
                summary="Landmark records present; confirm scope with LPC.",
                findings=[f"LPC dataset rows: {facts.get('landmark_row_count')}"],
                evidence=_evidence_items(payload),
                updated_at=_now(),
                generated_by=GENERATED_BY,
            )
        return DepartmentReview(
            department=Department.LANDMARKS,
            status=ReviewStatus.PASS,
            summary="No LPC landmark records on this BBL.",
            findings=[f"LPC dataset rows: {facts.get('landmark_row_count')}"],
            evidence=_evidence_items(payload),
            updated_at=_now(),
            generated_by=GENERATED_BY,
        )

    async def review_critic(self, *, reviews: list[DepartmentReview]) -> DepartmentReview:
        return critic_policy(reviews, generated_by=GENERATED_BY)

    async def review_named(
        self,
        department: Department,
        *,
        bbl: str,
        bin_: str,
        work_type: str,
        existing: list[DepartmentReview] | None = None,
    ) -> DepartmentReview:
        if department == Department.ZONING:
            return await self.review_zoning(bbl=bbl)
        if department == Department.BUILDING:
            return await self.review_building(bbl=bbl, bin_=bin_)
        if department == Department.FIRE:
            return await self.review_fire(bin_=bin_)
        if department == Department.UTILITIES:
            return await self.review_utilities(bbl=bbl, bin_=bin_)
        if department == Department.LANDMARKS:
            return await self.review_landmarks(bbl=bbl, work_type=work_type)
        if department == Department.HOUSING:
            return await self.review_housing(bin_=bin_)
        if department == Department.CRITIC:
            return await self.review_critic(reviews=existing or [])
        raise ValueError(f"Unknown department: {department}")

    async def related_permits(self, *, bbl: str, bin_: str) -> list[dict]:
        permits = await self._socrata.permits_by_bbl(bbl)
        if bin_:
            permits = permits + await self._socrata.permits_by_bin(bin_)
        seen: set[str] = set()
        rows: list[dict] = []
        for row in permits:
            key = str(
                row.get("job_filing_number")
                or row.get("job__")
                or row.get("job_")
                or row.get("job_number")
                or row.get("permit_si_no")
                or row.get("tracking_number")
                or ""
            )
            if not key:
                key = "|".join(
                    str(row.get(field) or "")
                    for field in ("work_type", "permit_status", "street_name", "house_no")
                )
            if key in seen:
                continue
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
