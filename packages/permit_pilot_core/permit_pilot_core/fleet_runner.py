from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Department, DepartmentReview, DepartmentStep
from permit_pilot_core.observability.traces import TraceRecorder
from permit_pilot_core.platform import memory as memory_bank
from permit_pilot_core.platform import runtime
from permit_pilot_core.platform.fleet import FLEET
from permit_pilot_core.settings import get_settings

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def init_department_steps() -> list[DepartmentStep]:
    return [
        DepartmentStep(name="distribution", department=Department(agent.department), status="pending")
        for agent in FLEET
        if agent.department
    ]


async def run_engine_distribution(
    store: FirestoreStore,
    engine: DistributionEngine,
    *,
    case_id: str,
    trace: TraceRecorder,
) -> list[DepartmentReview]:
    case = store.get_case(case_id)
    if not case:
        raise ValueError(f"Case not found: {case_id}")
    steps = init_department_steps()
    store.save_workflow_steps(case_id, steps)
    reviews: list[DepartmentReview] = []
    for step in steps:
        if step.department is None:
            continue
        step.status = "running"
        step.started_at = _now()
        store.save_workflow_steps(case_id, steps)
        with trace.span(
            f"department.{step.department.value}",
            actor=step.department.value,
            detail=f"Running {step.department.value}",
        ):
            review = await _run_department(
                engine,
                step.department,
                case_id=case_id,
                bbl=case.bbl,
                bin_=case.bin,
                work_type=case.work_type,
                existing=reviews,
            )
        reviews.append(review)
        step.status = "completed"
        step.detail = review.summary
        step.completed_at = _now()
        store.save_distribution(case_id, reviews)
        store.save_workflow_steps(case_id, steps)
        store.append_audit(case_id, actor=step.department.value, action="workflow_step_completed", detail=review.summary)
    return reviews


async def _run_department(
    engine: DistributionEngine,
    dept: Department,
    *,
    case_id: str,
    bbl: str,
    bin_: str,
    work_type: str,
    existing: list[DepartmentReview],
) -> DepartmentReview:
    if dept == Department.ZONING:
        return await engine.review_zoning(bbl=bbl)
    if dept == Department.BUILDING:
        return await engine.review_building(bbl=bbl, bin_=bin_)
    if dept == Department.FIRE:
        return await engine.review_fire(bin_=bin_)
    if dept == Department.UTILITIES:
        return await engine.review_utilities(bbl=bbl, bin_=bin_)
    if dept == Department.LANDMARKS:
        return await engine.review_landmarks(bbl=bbl, work_type=work_type)
    if dept == Department.HOUSING:
        return await engine.review_housing(bin_=bin_)
    if dept == Department.CRITIC:
        return await engine.review_critic(reviews=existing)
    raise ValueError(f"Unknown department: {dept}")


def invoke_orchestrator(store: FirestoreStore, *, case_id: str, user_id: str) -> str:
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
    except Exception as exc:
        logger.warning("Memory Bank retrieve failed for case %s: %s", case_id, exc)
        memories = []
    message = json.dumps(
        {
            "case_id": case.id,
            "address": case.address,
            "bbl": case.bbl,
            "bin": case.bin,
            "work_type": case.work_type,
            "parcel_memories": memories,
            "instruction": (
                "Run a full department distribution using MCP tools and persist_review. "
                "Then run validate_citations. Return a 3-sentence clerk briefing."
            ),
        }
    )
    events = runtime.stream_query(engine_id=engine_id, user_id=user_id, message=message)
    text = runtime.extract_text(events)
    try:
        memory_bank.generate_from_session(session=f"{engine_id}/sessions/{case_id}", bbl=case.bbl)
    except Exception as exc:
        logger.warning("Memory Bank generate_from_session failed for case %s: %s", case_id, exc)
    return text


async def run_distribution(
    store: FirestoreStore,
    engine: DistributionEngine,
    *,
    case_id: str,
    user_id: str = "system",
) -> list[DepartmentReview]:
    """Run live NYC Open Data distribution, then optionally the Agent Runtime orchestrator."""
    trace = TraceRecorder(store, case_id)
    settings = get_settings()
    reviews: list[DepartmentReview] = []

    with trace.span("distribution.run", actor="system", detail="NYC Open Data department distribution"):
        reviews = await run_engine_distribution(store, engine, case_id=case_id, trace=trace)

    if settings.orchestrator_engine_id:
        with trace.span(
            "runtime.orchestrator",
            actor="permit_orchestrator",
            detail="Agent Runtime orchestrator briefing",
            engine_id=settings.orchestrator_engine_id,
        ):
            try:
                briefing = invoke_orchestrator(store, case_id=case_id, user_id=user_id)
                if briefing:
                    store.save_briefing(
                        case_id,
                        summary=briefing,
                        model=settings.vertex_model,
                        generated_by="permit_orchestrator",
                    )
                    store.append_audit(
                        case_id,
                        actor="permit_orchestrator",
                        action="briefing_generated",
                        detail=briefing[:200],
                    )
            except Exception as exc:
                store.append_audit(
                    case_id,
                    actor="system",
                    action="orchestrator_error",
                    detail=str(exc),
                )
                raise

    return reviews
