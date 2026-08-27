from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Citation, Department, DepartmentReview, EvidenceItem, ReviewStatus
from permit_pilot_core.settings import get_settings

mcp = MCPServer(
    name="permit-tools",
    title="Permit Pilot NYC tools",
    description="Governed NYC Open Data tools for the Permit Pilot agent fleet.",
)
_engine = DistributionEngine()


def _store() -> FirestoreStore:
    return FirestoreStore(project_id=get_settings().project_id)


def _now() -> datetime:
    return datetime.now(UTC)


def _dump(review: DepartmentReview) -> dict[str, Any]:
    return json.loads(review.model_dump_json())


@mcp.tool()
async def lookup_pluto(bbl: str, case_id: str = "") -> dict[str, Any]:
    """Fetch DCP PLUTO zoning facts for a NYC BBL and optionally persist a zoning review."""
    review = await _engine.review_zoning(bbl=bbl)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_dob_permits(bbl: str, bin: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch DOB NOW permits and violations for a BBL/BIN."""
    review = await _engine.review_building(bbl=bbl, bin_=bin)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_dob_violations(bin: str, bbl: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch active DOB violations for a BIN."""
    review = await _engine.review_building(bbl=bbl, bin_=bin)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_fdny_violations(bin: str, case_id: str = "") -> dict[str, Any]:
    """Fetch FDNY violation records for a BIN."""
    review = await _engine.review_fire(bin_=bin)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_hpd_violations(bin: str, case_id: str = "") -> dict[str, Any]:
    """Fetch HPD violation records for a BIN."""
    review = await _engine.review_housing(bin_=bin)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_dep_ecb(bbl: str, bin: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch DEP ECB violation records for a parcel."""
    review = await _engine.review_utilities(bbl=bbl, bin_=bin)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def lookup_landmarks(bbl: str, work_type: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch LPC landmark records for a BBL."""
    review = await _engine.review_landmarks(bbl=bbl, work_type=work_type)
    if case_id:
        _merge_review(case_id, review)
    return _dump(review)


@mcp.tool()
async def validate_citations(case_id: str) -> dict[str, Any]:
    """Run the deterministic cite-or-reject critic against persisted department reviews."""
    store = _store()
    reviews = [r for r in store.list_distribution(case_id) if r.department != Department.CRITIC]
    critic = await _engine.review_critic(reviews=reviews)
    _merge_review(case_id, critic)
    return _dump(critic)


@mcp.tool()
async def persist_review(
    case_id: str,
    department: str,
    status: str,
    summary: str,
    findings_json: str = "[]",
    evidence_json: str = "[]",
    citations_json: str = "[]",
) -> dict[str, Any]:
    """Persist a department review onto the case file in Firestore."""
    findings = json.loads(findings_json) if findings_json else []
    evidence_raw = json.loads(evidence_json) if evidence_json else []
    citations_raw = json.loads(citations_json) if citations_json else []
    review = DepartmentReview(
        department=Department(department),
        status=ReviewStatus(status),
        summary=summary,
        findings=list(findings),
        evidence=[EvidenceItem.model_validate(item) for item in evidence_raw],
        citations=[Citation.model_validate(item) for item in citations_raw],
        updated_at=_now(),
    )
    _merge_review(case_id, review)
    return _dump(review)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    return JSONResponse({"status": "ok", "server": mcp.name})


def _merge_review(case_id: str, review: DepartmentReview) -> None:
    store = _store()
    existing = {r.department: r for r in store.list_distribution(case_id)}
    existing[review.department] = review
    store.save_distribution(case_id, list(existing.values()))
    store.append_audit(
        case_id,
        actor=review.department.value,
        action="mcp_review_persisted",
        detail=review.summary,
    )


def _transport_security() -> TransportSecuritySettings:
    # Cloud Run already validates Host. Locally keep DNS-rebinding protection.
    settings = get_settings()
    if settings.running_on_cloud_run:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1", "localhost", "127.0.0.1:*", "localhost:*"],
    )


app = mcp.streamable_http_app(stateless_http=True, transport_security=_transport_security())
