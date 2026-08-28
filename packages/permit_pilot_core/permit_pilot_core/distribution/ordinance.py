"""Ordinance search/get_section — BetaNYC-shaped corpus of NYC Charter, Admin Code, and Rules.

The critic must retrieve a section before accepting a citation. The bundled corpus is
the source of truth used at runtime; ORDINANCE_HINTS is only a department hint list.
"""

from __future__ import annotations

import re
from typing import Any

from permit_pilot_core.models import Department

# Department hint list — not the source of truth for whether a code exists.
ORDINANCE_HINTS: dict[str, set[Department]] = {
    "1 RCNY 101-07": {Department.BUILDING},
    "FC 901.7": {Department.FIRE},
    "HMC §27-2115": {Department.HOUSING},
    "27-2115": {Department.HOUSING},
    "DEP Rules": {Department.UTILITIES},
    "LPC Rule 2-01": {Department.LANDMARKS},
    "NYC LPC": {Department.LANDMARKS},
    "25-305": {Department.LANDMARKS},
    "BC 3301": {Department.BUILDING},
    "BC 28-104": {Department.BUILDING},
    "BC 28-105": {Department.BUILDING},
    "AC 28-105.12": {Department.BUILDING},
    "28-105": {Department.CRITIC, Department.BUILDING},
    "NYC Admin Code §28-105": {Department.CRITIC, Department.BUILDING},
}

CORPUS: list[dict[str, str]] = [
    {
        "citation": "28-105",
        "aliases": "NYC Admin Code §28-105, AC 28-105, BC 28-105, 28-105.12",
        "corpus": "admin_code",
        "heading": "Permits required",
        "text": (
            "It shall be unlawful to construct, enlarge, alter, repair, move, demolish, or change "
            "the occupancy or use of a building or structure, or to erect, install, enlarge, alter, "
            "repair, remove, convert or replace any gas, mechanical, plumbing or other system, "
            "or to cause any such work to be done, unless and until a written permit therefor shall "
            "have been issued by the commissioner in accordance with the requirements of this code. "
            "Department determinations must reference applicable code sections."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "1 RCNY 101-07",
        "aliases": "RCNY 101-07, 101-07",
        "corpus": "rules",
        "heading": "Open DOB violations and permit issuance",
        "text": (
            "Open Department of Buildings violations must be resolved or dismissed before permit "
            "approval for related work. The commissioner may require documented clearance of "
            "active violations as a condition of permit issuance."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "FC 901.7",
        "aliases": "Fire Code 901.7, 901.7",
        "corpus": "rules",
        "heading": "Fire protection systems — impairment and open violations",
        "text": (
            "Open fire code violations require correction or documented clearance before approval "
            "of related construction or alteration work. Impaired fire protection systems shall "
            "not remain out of service without required notifications and compensatory measures."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "27-2115",
        "aliases": "HMC §27-2115, Housing Maintenance Code 27-2115",
        "corpus": "admin_code",
        "heading": "Housing maintenance violations — penalties and correction",
        "text": (
            "Class A or B Housing Maintenance Code violations must be corrected. The department "
            "may issue orders requiring the owner to repair, and related permit work shall not "
            "proceed while Class A violations remain open without documented correction."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "25-305",
        "aliases": "NYC LPC, LPC Rule 2-01, Admin Code 25-305",
        "corpus": "admin_code",
        "heading": "Landmarks Preservation Commission — alterations and demolition",
        "text": (
            "It shall be unlawful to alter, reconstruct, or demolish a landmark or a building in "
            "an historic district, or to cause such work to be done, without a certificate of "
            "appropriateness or other approval issued by the Landmarks Preservation Commission."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "24-524",
        "aliases": "DEP Rules, DEP ECB, Admin Code 24-524",
        "corpus": "admin_code",
        "heading": "Environmental control board — water and sewer penalties",
        "text": (
            "Open DEP Environmental Control Board violations and unpaid penalties must be "
            "resolved before related permit approval. The commissioner may withhold permits "
            "where outstanding ECB judgments remain unsatisfied."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
    {
        "citation": "3301",
        "aliases": "BC 3301, Building Code Chapter 33",
        "corpus": "admin_code",
        "heading": "Safeguards during construction or demolition",
        "text": (
            "The provisions of this chapter shall apply to all construction, alteration, and "
            "demolition operations. Site safety plans and required safeguards shall be in place "
            "before such work proceeds."
        ),
        "source_url": "https://github.com/BetaNYC/nyc-charter-laws-rules",
    },
]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _score(query: str, entry: dict[str, str]) -> int:
    needle = query.lower().strip()
    if not needle:
        return 0
    blob = " ".join(entry.get(key, "") for key in ("citation", "aliases", "heading", "text")).lower()
    if needle in entry["citation"].lower() or needle in entry["aliases"].lower():
        return 100
    if needle in entry["heading"].lower():
        return 80
    if needle in blob:
        return 40
    tokens = [token for token in re.split(r"\s+", needle) if len(token) > 2]
    return sum(10 for token in tokens if token in blob)


def search_ordinance(query: str, *, corpus: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    scored = []
    for entry in CORPUS:
        if corpus != "all" and entry["corpus"] != corpus:
            continue
        score = _score(query, entry)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "citation": entry["citation"],
            "heading": entry["heading"],
            "corpus": entry["corpus"],
            "excerpt": entry["text"][:400],
            "source_url": entry["source_url"],
            "score": score,
        }
        for score, entry in scored[: max(1, min(limit, 50))]
    ]


def get_section(citation: str, *, corpus: str = "all") -> dict[str, Any]:
    needle = _normalize(citation)
    matches = []
    for entry in CORPUS:
        if corpus != "all" and entry["corpus"] != corpus:
            continue
        aliases = _normalize(entry["citation"] + " " + entry["aliases"])
        if needle and (needle in aliases or aliases in needle or needle == _normalize(entry["citation"])):
            matches.append(entry)
    if not matches:
        return {"found": False, "citation": citation, "matches": []}
    entry = matches[0]
    return {
        "found": True,
        "citation": entry["citation"],
        "heading": entry["heading"],
        "corpus": entry["corpus"],
        "text": entry["text"],
        "source_url": entry["source_url"],
        "aliases": entry["aliases"],
    }


def citation_resolves(code: str) -> bool:
    return bool(get_section(code).get("found"))


def citation_valid_for_department(code: str, department: Department) -> bool:
    if not citation_resolves(code):
        return False
    allowed = ORDINANCE_HINTS.get(code.strip())
    if allowed is None:
        # Resolved in corpus but not department-bound — critic still accepts existence.
        return True
    return department in allowed
