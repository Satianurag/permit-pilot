"""Raw NYC Open Data evidence for department agents. No PASS/FAIL here."""

from __future__ import annotations

from typing import Any

from permit_pilot_core.socrata import datasets as ds
from permit_pilot_core.socrata.client import SocrataClient

BOROUGH_NAMES = {
    "MN": "MANHATTAN",
    "BX": "BRONX",
    "BK": "BROOKLYN",
    "QN": "QUEENS",
    "SI": "STATEN ISLAND",
}


def house_number(address: str) -> str:
    token = address.strip().split(" ", 1)[0]
    return token.replace("'", "''")


def is_active_dob_violation(row: dict) -> bool:
    category = str(row.get("violation_category", "")).upper()
    if "ACTIVE" in category:
        return True
    if category and "CLOSED" in category:
        return False
    disposition = str(row.get("disposition_date", "")).strip()
    return not disposition


def is_open_hpd_violation(row: dict) -> bool:
    approved = str(row.get("approveddate", "")).strip()
    if approved:
        return False
    violation_class = str(row.get("class", "")).upper()
    return violation_class in {"A", "B", "C", "I"} or not approved


def is_open_fdny_violation(row: dict) -> bool:
    status = str(row.get("violation_status", row.get("status", ""))).upper()
    if not status:
        return False
    return status not in {"CLOSED", "DISMISSED", "RESOLVED", "PAID"}


def _pack(*, dataset_id: str, facts: dict[str, Any], rows: list[dict[str, Any]], note: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "NYC Open Data",
        "dataset_id": dataset_id,
        "facts": facts,
        "row_count": len(rows),
        "rows": rows[:15],
    }
    if note:
        payload["note"] = note
    return payload


class EvidenceClient:
    def __init__(self, socrata: SocrataClient | None = None) -> None:
        self._socrata = socrata or SocrataClient()

    async def lookup_pluto(self, bbl: str) -> dict[str, Any]:
        rows = await self._socrata.pluto_by_bbl(bbl)
        if not rows:
            return _pack(dataset_id=ds.PLUTO, facts={"found": False}, rows=[], note="No PLUTO record for this BBL.")
        lot = rows[0]
        facts = {
            "found": True,
            "zonedist1": lot.get("zonedist1") or lot.get("zonedist"),
            "landuse": lot.get("landuse"),
            "histdist": lot.get("histdist") or "",
            "address": lot.get("address"),
            "borough": lot.get("borough"),
            "ownername": lot.get("ownername") or lot.get("owner"),
            "latitude": lot.get("latitude"),
            "longitude": lot.get("longitude"),
        }
        return _pack(dataset_id=ds.PLUTO, facts=facts, rows=rows[:3])

    async def lookup_dob_permits(self, bbl: str, bin_: str = "") -> dict[str, Any]:
        permits = await self._socrata.permits_by_bbl(bbl)
        filings = await self._socrata.filings_by_bin(bin_) if bin_ else []
        facts = {
            "permit_count": len(permits),
            "filing_count": len(filings),
            "bin_present": bool(bin_),
        }
        return _pack(dataset_id=ds.PERMITS, facts=facts, rows=permits[:10])

    async def lookup_dob_violations(self, bin_: str) -> dict[str, Any]:
        if not bin_:
            return _pack(
                dataset_id=ds.DOB_VIOLATIONS,
                facts={"bin_present": False, "active_violation_count": 0},
                rows=[],
                note="BIN required for DOB violation lookup.",
            )
        rows = await self._socrata.dob_violations_by_bin(bin_)
        active = [row for row in rows if is_active_dob_violation(row)]
        facts = {
            "bin_present": True,
            "violation_row_count": len(rows),
            "active_violation_count": len(active),
        }
        return _pack(dataset_id=ds.DOB_VIOLATIONS, facts=facts, rows=active[:10] or rows[:5])

    async def lookup_fdny_violations(self, bin_: str) -> dict[str, Any]:
        if not bin_:
            return _pack(
                dataset_id=ds.FDNY_VIOLATIONS,
                facts={"bin_present": False, "open_violation_count": 0},
                rows=[],
                note="BIN required for FDNY violation lookup.",
            )
        rows = await self._socrata.fdny_violations_by_bin(bin_)
        open_rows = [row for row in rows if is_open_fdny_violation(row)]
        facts = {
            "bin_present": True,
            "record_count": len(rows),
            "open_violation_count": len(open_rows),
        }
        return _pack(dataset_id=ds.FDNY_VIOLATIONS, facts=facts, rows=open_rows[:10] or rows[:5])

    async def lookup_hpd_violations(self, bin_: str) -> dict[str, Any]:
        if not bin_:
            return _pack(
                dataset_id=ds.HPD_VIOLATIONS,
                facts={"bin_present": False, "open_hpd_violation_count": 0, "open_class_a_count": 0},
                rows=[],
                note="BIN required for HPD violation lookup.",
            )
        rows = await self._socrata.hpd_violations_by_bin(bin_)
        open_rows = [row for row in rows if is_open_hpd_violation(row)]
        class_a = [row for row in open_rows if str(row.get("class", "")).upper() == "A"]
        facts = {
            "bin_present": True,
            "row_count": len(rows),
            "open_hpd_violation_count": len(open_rows),
            "open_class_a_count": len(class_a),
        }
        return _pack(dataset_id=ds.HPD_VIOLATIONS, facts=facts, rows=open_rows[:10] or rows[:5])

    async def lookup_dep_ecb(self, bbl: str, bin_: str = "") -> dict[str, Any]:
        pluto_rows = await self._socrata.pluto_by_bbl(bbl)
        if not pluto_rows:
            return _pack(
                dataset_id=ds.DEP_ECB,
                facts={"found": False, "open_dep_ecb_count": 0},
                rows=[],
                note="No PLUTO record found for DEP ECB lookup.",
            )
        lot = pluto_rows[0]
        address = str(lot.get("address") or "")
        borough_code = str(lot.get("borough") or "")
        borough_name = BOROUGH_NAMES.get(borough_code.upper(), borough_code.upper())
        house = house_number(address)
        if not house or not borough_name:
            return _pack(
                dataset_id=ds.DEP_ECB,
                facts={"found": False, "open_dep_ecb_count": 0},
                rows=[],
                note="Address and borough required for DEP ECB lookup.",
            )
        rows = await self._socrata.dep_ecb_by_address(house=house, borough=borough_name)
        open_rows = [
            row
            for row in rows
            if str(row.get("compliance_status", "")).lower() not in {"dismissed", "paid in full"}
        ]
        facts = {
            "found": True,
            "address": address,
            "borough": borough_name,
            "dep_ecb_record_count": len(rows),
            "open_dep_ecb_count": len(open_rows),
            "bin": bin_,
        }
        return _pack(dataset_id=ds.DEP_ECB, facts=facts, rows=open_rows[:10] or rows[:5])

    async def lookup_landmarks(self, bbl: str, work_type: str = "") -> dict[str, Any]:
        rows = await self._socrata.landmarks_by_bbl(bbl)
        pluto = await self._socrata.pluto_by_bbl(bbl)
        histdist = pluto[0].get("histdist") if pluto else None
        facts = {
            "landmark_row_count": len(rows),
            "histdist": histdist or "",
            "in_landmark_context": bool(rows) or bool(histdist),
            "work_type": work_type,
            "demolition": "demolition" in work_type.lower(),
        }
        return _pack(dataset_id=ds.LANDMARKS, facts=facts, rows=rows[:10])
