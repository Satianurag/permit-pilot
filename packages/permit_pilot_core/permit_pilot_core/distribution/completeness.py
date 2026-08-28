"""DOB-style completeness gate. Technical agents do not run on incomplete filings."""

from __future__ import annotations

from typing import Any

from permit_pilot_core.models import Case, CompletenessScan


def scan_case(case: Case, *, packet_text: str = "", gemma: dict[str, Any] | None = None) -> CompletenessScan:
    findings: list[str] = []
    missing: list[str] = []
    if not case.bbl.strip():
        missing.append("BBL")
        findings.append("BBL is required to join NYC Open Data.")
    if not case.bin.strip():
        missing.append("BIN")
        findings.append("BIN is required for FDNY and HPD lookups. Incomplete filings get a checklist, not objections.")
    if not case.work_type.strip():
        missing.append("work_type")
        findings.append("Work type is required to route department specialists.")
    if not case.address.strip():
        missing.append("address")
        findings.append("Street address is required.")

    gemma_complete = True
    if gemma:
        gemma_complete = bool(gemma.get("complete_enough", True))
        for item in gemma.get("findings") or []:
            findings.append(f"Gemma: {item}")
        for item in gemma.get("missing") or []:
            if item not in missing:
                missing.append(str(item))

    demolition = "demolition" in case.work_type.lower()
    if demolition and not packet_text.strip():
        findings.append("Demolition filings should include an applicant packet or plan notes.")

    complete = not missing and gemma_complete
    checklist = ""
    if not complete:
        checklist = (
            "Incomplete submission checklist (not technical objections): "
            + "; ".join(missing or findings)
            + ". Resubmit with the missing identifiers before plan examination begins."
        )
    return CompletenessScan(
        complete_enough=complete,
        missing=missing,
        findings=findings,
        checklist=checklist,
        generated_by="completeness_scan",
        model=str((gemma or {}).get("model") or ""),
    )
