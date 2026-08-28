"""Canonical distribution path: completeness → routing plan → orchestrator A2A → selected engines → engine_fallback."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from permit_pilot_core.distribution.completeness import scan_case
from permit_pilot_core.distribution.critic import review_critic
from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.distribution.evidence import EvidenceClient
from permit_pilot_core.distribution.routing import plan_departments
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Case, CaseStatus, Department, DepartmentReview, DepartmentStep, ReviewStatus
from permit_pilot_core.observability.traces import TraceRecorder
from permit_pilot_core.orchestration.gemma import scan_packet_with_gemma
from permit_pilot_core.orchestration.vertex import orchestrate_case_summary
from permit_pilot_core.platform import memory as memory_bank
from permit_pilot_core.platform import runtime
from permit_pilot_core.platform.fleet import FLEET, department_agents
from permit_pilot_core.settings import get_settings

logger = logging.getLogger(__name__)

MAX_CRITIC_ITERATIONS = 3


def _now() -> datetime:
    return datetime.now(UTC)


def init_department_steps(departments: list[str] | None = None) -> list[DepartmentStep]:
    wanted = set(departments) if departments is not None else {agent.department for agent in department_agents()}
    return [
        DepartmentStep(name="distribution", department=Department(agent.department), status="pending")
        for agent in FLEET
        if agent.department and agent.department in wanted
    ]


def _merge(store: FirestoreStore, case_id: str, review: DepartmentReview) -> None:
    existing = {item.department: item for item in store.list_distribution(case_id)}
    existing[review.department] = review
    store.save_distribution(case_id, list(existing.values()))


def _packet_text(store: FirestoreStore, case_id: str) -> str:
    document = store.get_intake_document(case_id)
    return (document.redacted_text if document else "") or ""


def critic_offenders(critic: DepartmentReview) -> list[str]:
    blob = " ".join([critic.summary, *critic.findings]).lower()
    found: list[str] = []
    for dept in Department:
        if dept == Department.CRITIC:
            continue
        if dept.value in blob and dept.value not in found:
            found.append(dept.value)
    return found


def _completed_departments(store: FirestoreStore, case_id: str) -> set[str]:
    done: set[str] = set()
    for step in store.list_workflow_steps(case_id):
        if step.status == "completed" and step.department:
            done.add(step.department.value)
    for review in store.list_distribution(case_id):
        if review.department != Department.CRITIC and review.status != ReviewStatus.CHECKING:
            done.add(review.department.value)
    return done


def _resume_targets(store: FirestoreStore, case_id: str, planned: list[str], *, reason: str) -> list[str]:
    if reason in {"eventarc_claim_resume", "claim_response", "resume"}:
        existing = {r.department.value: r for r in store.list_distribution(case_id)}
        if reason == "resume":
            completed = _completed_departments(store, case_id)
            return [name for name in planned if name not in completed]
        targets: list[str] = []
        for name in planned:
            review = existing.get(name)
            if review is None or review.status in {ReviewStatus.FAIL, ReviewStatus.NEEDS_INFO, ReviewStatus.CHECKING}:
                targets.append(name)
        return targets
    return list(planned)


async def _scan_completeness(store: FirestoreStore, case: Case) -> None:
    packet = _packet_text(store, case.id)
    gemma = scan_packet_with_gemma(packet)
    scan = scan_case(case, packet_text=packet, gemma=gemma)
    store.save_completeness(case.id, scan)
    store.append_audit(
        case.id,
        actor="completeness_agent",
        action="completeness_scan",
        detail=scan.checklist or "Packet complete enough for technical review.",
    )


async def _persist_routing_plan(store: FirestoreStore, case: Case, *, complete_enough: bool) -> dict:
    memories: list[dict] = []
    try:
        memories = memory_bank.retrieve(bbl=case.bbl, query=case.work_type)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory Bank retrieve failed for case %s: %s", case.id, exc)
    pluto: dict = {}
    try:
        pluto = await EvidenceClient().lookup_pluto(case.bbl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PLUTO lookup failed for routing plan on %s: %s", case.id, exc)
    plan = plan_departments(
        work_type=case.work_type,
        bin_=case.bin,
        pluto=pluto,
        memories=memories,
        complete_enough=complete_enough,
    )
    plan["generated_by"] = "permit_orchestrator"
    store.save_routing_plan(case.id, plan)
    store.append_audit(case.id, actor="permit_orchestrator", action="routing_plan", detail=json.dumps(plan)[:500])
    return plan


def _mark_skipped(store: FirestoreStore, case_id: str, skipped: dict[str, str]) -> None:
    steps = [
        DepartmentStep(
            name="distribution",
            department=Department(name),
            status="skipped",
            detail=reason,
            completed_at=_now(),
        )
        for name, reason in skipped.items()
        if name in {item.value for item in Department}
    ]
    if steps:
        store.save_workflow_steps(case_id, steps)


def invoke_orchestrator(
    store: FirestoreStore,
    *,
    case_id: str,
    user_id: str,
    instruction: str | None = None,
) -> str:
    settings = get_settings()
    engine_id = settings.orchestrator_engine_id
    if not engine_id:
        raise RuntimeError("ORCHESTRATOR_ENGINE_ID is not configured")
    case = store.get_case(case_id)
    if not case:
        raise ValueError(f"Case not found: {case_id}")
    memories: list[dict] = []
    try:
        memories = memory_bank.retrieve(bbl=case.bbl, query=case.work_type)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory Bank retrieve failed for case %s: %s", case_id, exc)
        memories = []
    state = store.fleet_state(case_id)
    message = json.dumps(
        {
            "case_id": case.id,
            "address": case.address,
            "bbl": case.bbl,
            "bin": case.bin,
            "work_type": case.work_type,
            "completeness": state.get("completeness"),
            "routing_plan": state.get("routing_plan"),
            "critic_iterations": state.get("critic_iterations") or 0,
            "interrupt_requested": bool(state.get("interrupt_requested")),
            "parcel_memories": memories,
            "instruction": instruction
            or (
                "Write or confirm the routing plan, delegate only to selected specialists, "
                "run the critic loop, draft HITL claim/decision, and return a 3-sentence clerk briefing."
            ),
        }
    )
    events = runtime.stream_query(engine_id=engine_id, user_id=user_id, message=message)
    text = runtime.extract_text(events)
    try:
        memory_bank.generate_from_session(session=f"{engine_id}/sessions/{case_id}", bbl=case.bbl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory Bank generate_from_session failed for case %s: %s", case_id, exc)
    return text


async def _invoke_department_engine(
    *,
    engine_id: str,
    user_id: str,
    case: Case,
    department: str,
) -> str:
    message = json.dumps(
        {
            "case_id": case.id,
            "address": case.address,
            "bbl": case.bbl,
            "bin": case.bin,
            "work_type": case.work_type,
            "department": department,
            "instruction": f"Run the {department} review for this case and persist_review.",
        }
    )
    events = await asyncio.to_thread(
        runtime.stream_query, engine_id=engine_id, user_id=user_id, message=message
    )
    return runtime.extract_text(events)


async def _run_selected_engines(
    store: FirestoreStore,
    *,
    case: Case,
    departments: list[str],
    user_id: str,
    trace: TraceRecorder,
) -> list[DepartmentReview]:
    settings = get_settings()
    mapping = settings.engine_id_map
    steps = {step.department.value: step for step in store.list_workflow_steps(case.id) if step.department}

    async def run_one(name: str) -> DepartmentReview | None:
        if store.interrupt_requested(case.id):
            return None
        engine_id = mapping.get(f"{name}_agent") or mapping.get(name)
        if not engine_id:
            return None
        step = steps.get(name)
        if step:
            step.status = "running"
            step.started_at = _now()
            step.engine_id = engine_id
            store.save_workflow_steps(case.id, list(steps.values()))
        with trace.span(
            f"a2a.{name}",
            actor=f"{name}_agent",
            detail=f"Remote A2A / stream_query {name}",
            engine_id=engine_id,
        ):
            try:
                await _invoke_department_engine(engine_id=engine_id, user_id=user_id, case=case, department=name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Department engine %s failed: %s", name, exc)
                if step:
                    step.status = "failed"
                    step.detail = str(exc)
                    step.completed_at = _now()
                    store.save_workflow_steps(case.id, list(steps.values()))
                return None
        reviews = {item.department.value: item for item in store.list_distribution(case.id)}
        review = reviews.get(name)
        if step:
            step.status = "completed" if review else "failed"
            step.detail = review.summary if review else "Engine returned no persist_review"
            step.completed_at = _now()
            store.save_workflow_steps(case.id, list(steps.values()))
        return review

    pending = [name for name in departments if f"{name}_agent" in mapping or name in mapping]
    if not pending:
        return []
    gathered = await asyncio.gather(*[run_one(name) for name in pending])
    return [item for item in gathered if item is not None]


async def _engine_fallback_selected(
    store: FirestoreStore,
    engine: DistributionEngine,
    *,
    case: Case,
    departments: list[str],
    trace: TraceRecorder,
) -> list[DepartmentReview]:
    steps = {step.department.value: step for step in store.list_workflow_steps(case.id) if step.department}
    reviews: list[DepartmentReview] = []
    for name in departments:
        if store.interrupt_requested(case.id):
            break
        dept = Department(name)
        step = steps.get(name)
        if step:
            step.status = "running"
            step.started_at = _now()
            store.save_workflow_steps(case.id, list(steps.values()))
        with trace.span(
            f"department.{name}",
            actor=name,
            detail=f"engine_fallback {name}",
        ):
            review = await engine.review_named(dept, bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
        review.generated_by = review.generated_by or "engine_fallback"
        _merge(store, case.id, review)
        reviews.append(review)
        if step:
            step.status = "completed"
            step.detail = review.summary
            step.completed_at = _now()
            store.save_workflow_steps(case.id, list(steps.values()))
        store.append_audit(case.id, actor=name, action="workflow_step_completed", detail=review.summary)
    return reviews


async def _critic_loop(
    store: FirestoreStore,
    engine: DistributionEngine,
    *,
    case: Case,
    planned: list[str],
    user_id: str,
    trace: TraceRecorder,
) -> list[DepartmentReview]:
    settings = get_settings()
    iterations = store.get_critic_iterations(case.id)
    reviews = [item for item in store.list_distribution(case.id) if item.department != Department.CRITIC]
    while iterations < MAX_CRITIC_ITERATIONS:
        if store.interrupt_requested(case.id):
            break
        with trace.span("critic.loop", actor="critic_agent", detail=f"iteration {iterations + 1}"):
            critic_engine_id = settings.engine_id_map.get("critic_agent")
            if critic_engine_id:
                try:
                    await _invoke_department_engine(
                        engine_id=critic_engine_id, user_id=user_id, case=case, department="critic"
                    )
                    persisted = store.list_distribution(case.id)
                    critic = next((item for item in persisted if item.department == Department.CRITIC), None)
                    if critic is None:
                        critic = review_critic(reviews)
                        _merge(store, case.id, critic)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Critic engine failed, using policy: %s", exc)
                    critic = review_critic(reviews)
                    _merge(store, case.id, critic)
            else:
                critic = review_critic(reviews)
                _merge(store, case.id, critic)
        iterations += 1
        store.set_critic_iterations(case.id, iterations)
        if critic.status == ReviewStatus.PASS:
            break
        offenders = [name for name in critic_offenders(critic) if name in planned]
        if not offenders:
            break
        store.append_audit(
            case.id,
            actor="critic_agent",
            action="critic_reroute",
            detail=f"FAIL re-route to {', '.join(offenders)} (iteration {iterations})",
        )
        await _run_selected_engines(
            store, case=case, departments=offenders, user_id=user_id, trace=trace
        )
        remaining = [
            name
            for name in offenders
            if name not in {item.department.value for item in store.list_distribution(case.id)}
        ]
        if remaining:
            await _engine_fallback_selected(
                store, engine, case=case, departments=remaining, trace=trace
            )
        reviews = [item for item in store.list_distribution(case.id) if item.department != Department.CRITIC]
    return store.list_distribution(case.id)


def _maybe_draft_hitl(store: FirestoreStore, case: Case, reviews: list[DepartmentReview]) -> None:
    if store.get_pending_hitl(case.id):
        return
    technical = [item for item in reviews if item.department != Department.CRITIC]
    if not technical:
        return
    failing = [item for item in technical if item.status in {ReviewStatus.FAIL, ReviewStatus.NEEDS_INFO}]
    if failing:
        message = "Applicant package: " + "; ".join(f"{item.department.value}: {item.summary}" for item in failing)
        store.save_pending_hitl(
            case.id,
            {"kind": "send_claim", "payload": {"message": message}, "confirmed": False},
        )
        store.set_case_status(case.id, CaseStatus.AWAITING_CLERK)
        return
    store.save_pending_hitl(
        case.id,
        {
            "kind": "record_decision",
            "payload": {"decision": "approve", "note": "All technical departments PASS. Clerk confirmation required.", "override": False},
            "confirmed": False,
        },
    )
    store.set_case_status(case.id, CaseStatus.AWAITING_CLERK)


def _save_briefing(store: FirestoreStore, case: Case, text: str, *, generated_by: str) -> None:
    if not text.strip():
        return
    store.save_briefing(
        case.id,
        summary=text.strip(),
        model=get_settings().vertex_model,
        generated_by=generated_by,
    )
    store.append_audit(case.id, actor=generated_by, action="briefing_generated", detail=text[:200])


async def run_distribution(
    store: FirestoreStore,
    engine: DistributionEngine,
    *,
    case_id: str,
    user_id: str = "system",
    reason: str = "intake",
) -> list[DepartmentReview]:
    """Completeness gate, routing plan, then orchestrator. Engines and engine_fallback are labeled fallbacks."""
    case = store.get_case(case_id)
    if not case:
        raise ValueError(f"Case not found: {case_id}")
    trace = TraceRecorder(store, case_id)
    settings = get_settings()

    with trace.span("distribution.run", actor="permit_orchestrator", detail=f"reason={reason}"):
        await _scan_completeness(store, case)
        completeness = store.get_completeness(case_id) or {}
        complete_enough = bool(completeness.get("complete_enough"))
        plan = await _persist_routing_plan(store, case, complete_enough=complete_enough)

        if not complete_enough:
            checklist = str(completeness.get("checklist") or "Incomplete filing — submit missing identifiers.")
            store.save_pending_hitl(
                case_id,
                {"kind": "send_claim", "payload": {"message": checklist}, "confirmed": False},
            )
            store.set_case_status(case_id, CaseStatus.AWAITING_CLERK)
            _mark_skipped(store, case_id, plan.get("skipped") or {})
            store.append_audit(case_id, actor="completeness_agent", action="completeness_pause", detail=checklist[:400])
            return []

        planned = _resume_targets(store, case_id, list(plan.get("departments") or []), reason=reason)
        steps = init_department_steps(planned)
        store.save_workflow_steps(case_id, steps)
        _mark_skipped(store, case_id, plan.get("skipped") or {})

        briefing = ""
        if settings.orchestrator_engine_id:
            if store.interrupt_requested(case_id):
                store.append_audit(case_id, actor="system", action="distribution_interrupted", detail="Before orchestrator A2A hop")
                return store.list_distribution(case_id)
            with trace.span(
                "runtime.orchestrator",
                actor="permit_orchestrator",
                detail="Coordinator stream_query",
                engine_id=settings.orchestrator_engine_id,
            ):
                try:
                    briefing = invoke_orchestrator(store, case_id=case_id, user_id=user_id)
                    if briefing:
                        _save_briefing(store, case, briefing, generated_by="permit_orchestrator")
                except Exception as exc:  # noqa: BLE001
                    store.append_audit(case_id, actor="system", action="orchestrator_error", detail=str(exc))
                    logger.warning("Orchestrator invoke failed: %s", exc)

        reviews = store.list_distribution(case_id)
        covered = {item.department.value for item in reviews if item.department != Department.CRITIC}
        missing = [name for name in planned if name not in covered]
        if missing and not store.interrupt_requested(case_id):
            with trace.span("runtime.selected_engines", actor="permit_orchestrator", detail=",".join(missing)):
                await _run_selected_engines(
                    store, case=case, departments=missing, user_id=user_id, trace=trace
                )
            reviews = store.list_distribution(case_id)
            covered = {item.department.value for item in reviews if item.department != Department.CRITIC}
            missing = [name for name in planned if name not in covered]

        if missing and not store.interrupt_requested(case_id):
            with trace.span("engine_fallback", actor="system", detail=",".join(missing)):
                await _engine_fallback_selected(
                    store, engine, case=case, departments=missing, trace=trace
                )

        if store.interrupt_requested(case_id):
            remaining = store.list_workflow_steps(case_id)
            for step in remaining:
                if step.status in {"pending", "running"}:
                    step.status = "interrupted"
                    step.detail = "Interrupt requested before A2A hop"
                    step.completed_at = _now()
            store.save_workflow_steps(case_id, remaining)
            store.append_audit(case_id, actor="system", action="distribution_interrupted", detail="Mid-run interrupt")
            return store.list_distribution(case_id)

        reviews = await _critic_loop(
            store, engine, case=case, planned=planned, user_id=user_id, trace=trace
        )
        _maybe_draft_hitl(store, case, reviews)
        if not store.get_briefing(case_id):
            try:
                summary = orchestrate_case_summary(case, reviews)
                _save_briefing(store, case, summary, generated_by="briefing_fallback")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Briefing fallback failed: %s", exc)
        return store.list_distribution(case_id)
