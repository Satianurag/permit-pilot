from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from permit_pilot_core.distribution.critic import review_critic
from permit_pilot_core.distribution.evidence import EvidenceClient
from permit_pilot_core.distribution.ordinance import get_section, search_ordinance
from permit_pilot_core.distribution.routing import plan_departments
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Citation, Department, DepartmentReview, EvidenceItem, ObjectionItem, ReviewStatus
from permit_pilot_core.settings import get_settings

mcp = MCPServer(
    name="permit-tools",
    title="Permit Pilot NYC tools",
    description="Governed NYC Open Data and ordinance tools for the Permit Pilot agent fleet.",
)
_evidence = EvidenceClient()


def _store() -> FirestoreStore:
    return FirestoreStore(project_id=get_settings().project_id)


def _now() -> datetime:
    return datetime.now(UTC)


@mcp.tool()
async def lookup_pluto(bbl: str, case_id: str = "") -> dict[str, Any]:
    """Fetch raw DCP PLUTO zoning facts for a NYC BBL. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_pluto(bbl)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_dob_permits(bbl: str, bin: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch raw DOB NOW permit and filing rows. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_dob_permits(bbl, bin)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_dob_violations(bin: str, bbl: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch raw DOB violation rows with descriptions. Counts are context, not a verdict."""
    payload = await _evidence.lookup_dob_violations(bin, bbl=bbl)
    payload["bbl"] = bbl
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_fdny_violations(bin: str, case_id: str = "") -> dict[str, Any]:
    """Fetch raw FDNY violation rows and open_violation_count. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_fdny_violations(bin)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_hpd_violations(bin: str, case_id: str = "", bbl: str = "") -> dict[str, Any]:
    """Fetch raw HPD violation rows by BBL (block/lot) and optional BIN. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_hpd_violations(bin, bbl=bbl)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_dep_ecb(bbl: str, bin: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch raw DEP ECB rows and open_dep_ecb_count. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_dep_ecb(bbl, bin)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def lookup_landmarks(bbl: str, work_type: str = "", case_id: str = "") -> dict[str, Any]:
    """Fetch raw LPC landmark rows and historic-district facts. Does not decide PASS/FAIL."""
    payload = await _evidence.lookup_landmarks(bbl, work_type)
    payload["case_id"] = case_id
    return payload


@mcp.tool()
async def search_ordinance_corpus(query: str, corpus: str = "all", limit: int = 10) -> dict[str, Any]:
    """Search NYC Charter / Admin Code / Rules (BetaNYC-shaped corpus)."""
    return {"query": query, "results": search_ordinance(query, corpus=corpus, limit=limit)}


@mcp.tool()
async def get_ordinance_section(citation: str, corpus: str = "all") -> dict[str, Any]:
    """Retrieve a NYC ordinance section by citation. Critic must call this before accepting a code."""
    return get_section(citation, corpus=corpus)


@mcp.tool()
async def persist_routing_plan(
    case_id: str,
    departments_json: str,
    skipped_json: str = "{}",
    reason: str = "technical_review",
) -> dict[str, Any]:
    """Persist the coordinator routing plan onto the case file."""
    departments = json.loads(departments_json) if departments_json else []
    skipped = json.loads(skipped_json) if skipped_json else {}
    plan = {
        "departments": departments,
        "skipped": skipped,
        "include_critic": bool(departments),
        "reason": reason,
        "generated_by": "permit_orchestrator",
    }
    store = _store()
    store.save_routing_plan(case_id, plan)
    store.append_audit(case_id, actor="permit_orchestrator", action="routing_plan", detail=json.dumps(plan)[:500])
    return plan


@mcp.tool()
async def suggest_routing_plan(bbl: str, bin: str, work_type: str, case_id: str = "") -> dict[str, Any]:
    """Compute a routing plan from live PLUTO + work type. Coordinator should persist it."""
    pluto = await _evidence.lookup_pluto(bbl)
    plan = plan_departments(work_type=work_type, bin_=bin, pluto=pluto, complete_enough=True)
    if case_id:
        _store().save_routing_plan(case_id, {**plan, "generated_by": "permit_orchestrator"})
    return plan


@mcp.tool()
async def validate_citations(case_id: str) -> dict[str, Any]:
    """Run cite-or-reject against persisted department reviews. Does not invent codes."""
    store = _store()
    reviews = [r for r in store.list_distribution(case_id) if r.department != Department.CRITIC]
    critic = review_critic(reviews)
    _merge_review(case_id, critic)
    return json.loads(critic.model_dump_json())


@mcp.tool()
async def persist_review(
    case_id: str,
    department: str,
    status: str,
    summary: str,
    findings_json: str = "[]",
    evidence_json: str = "[]",
    citations_json: str = "[]",
    objections_json: str = "[]",
    generated_by: str = "",
) -> dict[str, Any]:
    """Persist a department review onto the case file in Firestore."""
    findings = json.loads(findings_json) if findings_json else []
    evidence_raw = json.loads(evidence_json) if evidence_json else []
    citations_raw = json.loads(citations_json) if citations_json else []
    objections_raw = json.loads(objections_json) if objections_json else []
    review = DepartmentReview(
        department=Department(department),
        status=ReviewStatus(status),
        summary=summary,
        findings=list(findings),
        evidence=[EvidenceItem.model_validate(item) for item in evidence_raw],
        citations=[Citation.model_validate(item) for item in citations_raw],
        objections=[ObjectionItem.model_validate(item) for item in objections_raw],
        updated_at=_now(),
        generated_by=generated_by or department,
        model=get_settings().vertex_model,
    )
    _merge_review(case_id, review)
    return json.loads(review.model_dump_json())


@mcp.tool()
async def draft_claim(case_id: str, message: str) -> dict[str, Any]:
    """Draft an applicant claim. Does not send. Clerk confirmation is required."""
    store = _store()
    store.save_pending_hitl(case_id, {"kind": "send_claim", "payload": {"message": message}, "confirmed": False})
    store.append_audit(case_id, actor="completeness_agent", action="claim_drafted", detail=message[:300])
    return {"queued": True, "kind": "send_claim", "message": message, "confirmed": False}


@mcp.tool()
async def draft_decision(case_id: str, decision: str, note: str, override: bool = False) -> dict[str, Any]:
    """Draft a clerk decision. Does not approve. Clerk confirmation is required."""
    store = _store()
    pending = {
        "kind": "record_decision",
        "payload": {"decision": decision, "note": note, "override": override},
        "confirmed": False,
    }
    store.save_pending_hitl(case_id, pending)
    store.append_audit(case_id, actor="permit_orchestrator", action="decision_drafted", detail=f"{decision}: {note[:200]}")
    return {**pending, "queued": True}


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
    settings = get_settings()
    if settings.running_on_cloud_run:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1", "localhost", "127.0.0.1:*", "localhost:*"],
    )


app = mcp.streamable_http_app(stateless_http=True, transport_security=_transport_security())
