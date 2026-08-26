"""Known NYC ordinance citations used by department reviews and the Critic policy check."""

from permit_pilot_core.models import Department

# code -> departments that may cite it
ORDINANCE_INDEX: dict[str, set[Department]] = {
    "1 RCNY 101-07": {Department.BUILDING},
    "FC 901.7": {Department.FIRE},
    "HMC §27-2115": {Department.HOUSING},
    "DEP Rules": {Department.UTILITIES},
    "LPC Rule 2-01": {Department.LANDMARKS},
    "NYC LPC": {Department.LANDMARKS},
    "BC 3301": {Department.BUILDING},
    "BC 28-104": {Department.BUILDING},
    "BC 28-105": {Department.BUILDING},
    "AC 28-105.12": {Department.BUILDING},
    "NYC Admin Code §28-105": {Department.CRITIC, Department.BUILDING},
}


def citation_valid_for_department(code: str, department: Department) -> bool:
    allowed = ORDINANCE_INDEX.get(code.strip())
    if not allowed:
        return False
    return department in allowed


def is_known_citation(code: str) -> bool:
    return code.strip() in ORDINANCE_INDEX
