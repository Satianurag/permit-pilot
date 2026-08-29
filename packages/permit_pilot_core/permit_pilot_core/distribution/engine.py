"""Engine fallback: evidence-only NEEDS_INFO reviews when Agent Runtime is down."""

from __future__ import annotations

from datetime import UTC, datetime

from permit_pilot_core.distribution.critic import review_critic as critic_policy
from permit_pilot_core.distribution.evidence import EvidenceClient
from permit_pilot_core.models import Department, DepartmentReview, EvidenceItem, ReviewStatus
from permit_pilot_core.socrata.client import SocrataClient

GENERATED_BY = "engine_fallback"
FALLBACK_SUMMARY = "Automatic review unavailable. City records are attached for you to read."


def _now() -> datetime:
    return datetime.now(UTC)


def _evidence_items(payload: dict) -> list[EvidenceItem]:
    dataset_id = str(payload.get("dataset_id") or "")
    items: list[EvidenceItem] = []
    for label, value in (payload.get("facts") or {}).items():
        items.append(EvidenceItem(source="NYC Open Data", dataset_id=dataset_id, label=str(label), value=value))
    return items


def _degraded(department: Department, *payloads: dict, extra: list[str] | None = None) -> DepartmentReview:
    findings = list(extra or [])
    evidence: list[EvidenceItem] = []
    for payload in payloads:
        note = str(payload.get("note") or "").strip()
        if note and note not in findings:
            findings.append(note)
        evidence.extend(_evidence_items(payload))
    findings.append(FALLBACK_SUMMARY)
    return DepartmentReview(
        department=department,
        status=ReviewStatus.NEEDS_INFO,
        summary=FALLBACK_SUMMARY,
        findings=findings,
        evidence=evidence,
        updated_at=_now(),
        generated_by=GENERATED_BY,
    )


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
            await self.review_housing(bin_=bin_, bbl=bbl),
        ]

    async def run_all(self, *, bbl: str, bin_: str, work_type: str) -> list[DepartmentReview]:
        reviews = await self.run_departments(bbl=bbl, bin_=bin_, work_type=work_type)
        reviews.append(await self.review_critic(reviews=reviews))
        return reviews

    async def review_zoning(self, *, bbl: str) -> DepartmentReview:
        payload = await self._evidence.lookup_pluto(bbl)
        facts = payload.get("facts") or {}
        extra = []
        if facts.get("found"):
            extra.append(f"Zoning district on file: {facts.get('zonedist1') or 'unknown'}.")
        return _degraded(Department.ZONING, payload, extra=extra)

    async def review_building(self, *, bbl: str, bin_: str) -> DepartmentReview:
        permits = await self._evidence.lookup_dob_permits(bbl, bin_)
        violations = await self._evidence.lookup_dob_violations(bin_, bbl=bbl)
        return _degraded(Department.BUILDING, permits, violations)

    async def review_fire(self, *, bin_: str) -> DepartmentReview:
        payload = await self._evidence.lookup_fdny_violations(bin_)
        return _degraded(Department.FIRE, payload)

    async def review_housing(self, *, bin_: str, bbl: str = "") -> DepartmentReview:
        payload = await self._evidence.lookup_hpd_violations(bin_, bbl=bbl)
        return _degraded(Department.HOUSING, payload)

    async def review_utilities(self, *, bbl: str, bin_: str) -> DepartmentReview:
        payload = await self._evidence.lookup_dep_ecb(bbl, bin_)
        return _degraded(Department.UTILITIES, payload)

    async def review_landmarks(self, *, bbl: str, work_type: str) -> DepartmentReview:
        payload = await self._evidence.lookup_landmarks(bbl, work_type)
        return _degraded(Department.LANDMARKS, payload)

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
            return await self.review_housing(bin_=bin_, bbl=bbl)
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
