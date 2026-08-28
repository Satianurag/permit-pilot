"""Intelligent department routing from work type, PLUTO facts, and completeness."""

from __future__ import annotations

from typing import Any

from permit_pilot_core.models import Department

TECHNICAL_DEPARTMENTS = (
    Department.ZONING,
    Department.BUILDING,
    Department.FIRE,
    Department.UTILITIES,
    Department.LANDMARKS,
    Department.HOUSING,
)


def plan_departments(
    *,
    work_type: str,
    bin_: str,
    pluto: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
    complete_enough: bool = True,
) -> dict[str, Any]:
    """Return selected departments and skip reasons. Critic runs only after technical work."""
    facts = (pluto or {}).get("facts") or {}
    histdist = str(facts.get("histdist") or "").strip()
    in_landmark = bool(facts.get("in_landmark_context")) or bool(histdist)
    work = work_type.lower()
    demolition = "demolition" in work
    plumbing = "plumbing" in work
    memory_landmark = any(
        "landmark" in str(item).lower() or "historic" in str(item).lower() for item in (memories or [])
    )

    skipped: dict[str, str] = {}
    if not complete_enough:
        for dept in TECHNICAL_DEPARTMENTS:
            skipped[dept.value] = "Filing is incomplete — NYC plan exam does not start technical objections yet."
        return {
            "departments": [],
            "skipped": skipped,
            "include_critic": False,
            "reason": "incomplete_filing",
            "histdist": histdist,
            "demolition": demolition,
        }

    selected: list[str] = [Department.ZONING.value, Department.BUILDING.value, Department.UTILITIES.value]

    if bin_.strip():
        selected.extend([Department.FIRE.value, Department.HOUSING.value])
    else:
        skipped[Department.FIRE.value] = "BIN required for FDNY lookup."
        skipped[Department.HOUSING.value] = "BIN required for HPD lookup."

    if demolition or in_landmark or memory_landmark:
        selected.append(Department.LANDMARKS.value)
    elif plumbing and not in_landmark and not memory_landmark:
        skipped[Department.LANDMARKS.value] = (
            "Plumbing work with empty PLUTO histdist and no landmark memory — LPC not in routing plan."
        )
    else:
        selected.append(Department.LANDMARKS.value)

    seen: set[str] = set()
    ordered: list[str] = []
    for name in selected:
        if name not in seen and name not in skipped:
            seen.add(name)
            ordered.append(name)

    return {
        "departments": ordered,
        "skipped": skipped,
        "include_critic": True,
        "reason": "technical_review",
        "histdist": histdist,
        "demolition": demolition,
    }
